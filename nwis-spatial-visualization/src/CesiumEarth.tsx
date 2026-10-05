import * as React from 'react';
import {
  ArcGisMapServerImageryProvider, ArcGISTiledElevationTerrainProvider, CallbackProperty, Cartesian2, Cartesian3, Color, Credit, NearFarScalar,
  EllipsoidTerrainProvider, GeoJsonDataSource, HeightReference, Ion, Math as CesiumMath, ScreenSpaceEventHandler,
  ScreenSpaceEventType, Viewer, createGooglePhotorealistic3DTileset, createWorldTerrainAsync, Cartographic,
  sampleTerrainMostDetailed, HeadingPitchRoll, Transforms,
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import type { Stage, Well } from './data-contract';
import { feature } from 'topojson-client';
import type { Topology } from 'topojson-specification';
import worldCountries from 'world-atlas/countries-110m.json';
import { formatDistanceKm, haversineKm, nearbyWells } from './spatialFrame';
import './cesium-earth.css';

interface Props {
  stage: Stage;
  surfaceContext?: boolean;
  wells: Well[];
  active: Well | null;
  radiusKm: number;
  selectedId: string | null;
  dorsIds: string[];
  sourceLabel: string;
  onSelect: (wellId: string) => void;
  onSurfaceStatus: (status: 'satellite' | 'terrain' | 'photoreal' | 'fallback') => void;
}

const GOOGLE_MAPS_3D_KEY = import.meta.env.VITE_GOOGLE_MAPS_3D_KEY?.trim();
const ION_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN?.trim();
const FIELD_ALTITUDE = (radiusKm: number) => Math.max(9_000, Math.min(65_000, radiusKm * 4_200));

async function addOfflineCountryBoundaries(viewer: Viewer) {
  const topology = worldCountries as unknown as Topology;
  const countries = feature(topology, topology.objects.countries);
  const source = await GeoJsonDataSource.load(countries, {
    stroke: Color.fromCssColorString('#8ba8aa').withAlpha(0.6),
    fill: Color.fromCssColorString('#46606a').withAlpha(0.34),
    strokeWidth: 0.65,
    clampToGround: true,
  });
  if (!viewer.isDestroyed()) viewer.dataSources.add(source);
}

function validLocation(well: Well): well is Well & { latitude: number; longitude: number } {
  return typeof well.latitude === 'number' && Number.isFinite(well.latitude)
    && typeof well.longitude === 'number' && Number.isFinite(well.longitude);
}

export function CesiumEarth({ stage, surfaceContext = false, wells, active, radiusKm, selectedId, dorsIds, sourceLabel, onSelect, onSurfaceStatus }: Props) {
  const hostRef = React.useRef<HTMLDivElement>(null);
  const viewerRef = React.useRef<Viewer | null>(null);
  const selectionRef = React.useRef(onSelect);
  const statusRef = React.useRef(onSurfaceStatus);
  const [engineError, setEngineError] = React.useState('');
  const [surfaceLabel, setSurfaceLabel] = React.useState(GOOGLE_MAPS_3D_KEY ? 'LOADING PHOTOREALISTIC TILES' : 'SATELLITE IMAGERY');
  const [locating, setLocating] = React.useState(false);
  const [terrainRevision, setTerrainRevision] = React.useState(0);
  const [surfaceElevation, setSurfaceElevation] = React.useState<number | null>(null);
  const [elevationState, setElevationState] = React.useState<'loading' | 'available' | 'unavailable'>('loading');
  const [povView, setPovView] = React.useState(false);
  const radiusTweenRef = React.useRef({ fromMeters: radiusKm * 1000, toMeters: radiusKm * 1000, startedAt: 0 });

  const zoomEarth = React.useCallback((direction: 1 | -1, steps = 1) => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    const height = viewer.camera.positionCartographic.height;
    const factor = Math.pow(1.28, Math.max(0.15, Math.min(steps, 5)));
    const available = direction > 0 ? Math.max(0, height - 120) : Math.max(0, 45_000_000 - height);
    const distance = Math.min(available, height * (direction > 0 ? 1 - 1 / factor : factor - 1));
    if (distance <= 0) return;
    // The Cesium zoomIn/zoomOut helpers honor the controller's zoom state and
    // can become no-ops when default wheel zoom is disabled. Move along the
    // camera axis directly so buttons and our canvas wheel handler share one
    // reliable path. A height-based cap prevents crossing the globe.
    if (direction > 0) viewer.camera.moveForward(distance);
    else viewer.camera.moveBackward(distance);
  }, []);

  React.useEffect(() => { selectionRef.current = onSelect; }, [onSelect]);
  React.useEffect(() => { statusRef.current = onSurfaceStatus; }, [onSurfaceStatus]);

  React.useEffect(() => {
    if (!hostRef.current) return;
    let disposed = false;
    let clickHandler: ScreenSpaceEventHandler | null = null;
    let tileset: { show?: boolean } | null = null;
    let imageryFailed = false;
    let fallbackPromise: Promise<void> | null = null;
    let viewer: Viewer;
    let canvas: HTMLCanvasElement | null = null;
    let onWheelZoom: ((event: WheelEvent) => void) | null = null;
    try {
      if (ION_TOKEN) Ion.defaultAccessToken = ION_TOKEN;
      viewer = new Viewer(hostRef.current, {
        animation: false, timeline: false, geocoder: false, baseLayerPicker: false,
        sceneModePicker: false, navigationHelpButton: false, homeButton: false,
        infoBox: false, selectionIndicator: false, fullscreenButton: false,
        baseLayer: false, terrainProvider: new EllipsoidTerrainProvider(),
        requestRenderMode: false, maximumRenderTimeChange: Infinity,
      });
      viewerRef.current = viewer;
      viewer.scene.backgroundColor = Color.fromCssColorString('#081117');
      viewer.scene.globe.baseColor = Color.fromCssColorString('#111d23');
      viewer.scene.globe.enableLighting = true;
      viewer.scene.screenSpaceCameraController.minimumZoomDistance = 80;
      viewer.scene.screenSpaceCameraController.maximumZoomDistance = 45_000_000;
      // Route wheel zoom through this canvas explicitly. The browser page can
      // otherwise consume wheel input before Cesium's default handler sees it.
      viewer.scene.screenSpaceCameraController.enableZoom = false;
      canvas = viewer.scene.canvas;
      const earthCanvas = canvas;
      onWheelZoom = (event: WheelEvent) => {
        event.preventDefault();
        event.stopPropagation();
        const pixels = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? event.deltaY * 16
          : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? event.deltaY * earthCanvas.clientHeight
            : event.deltaY;
        zoomEarth(pixels < 0 ? 1 : -1, Math.max(0.15, Math.min(5, Math.abs(pixels) / 100)));
      };
      canvas.addEventListener('wheel', onWheelZoom, { passive: false });
      canvas.style.touchAction = 'none';

      // Elevation is independent of the satellite imagery. Prefer Cesium
      // World Terrain when configured; otherwise use Esri's public global
      // elevation service and keep the ellipsoid only as the final fallback.
      const loadTerrain = async () => {
        if (ION_TOKEN) {
          try {
            const terrain = await createWorldTerrainAsync({ requestVertexNormals: true, requestWaterMask: true });
            if (!disposed) {
              viewer.terrainProvider = terrain;
              setTerrainRevision(value => value + 1);
              if (!GOOGLE_MAPS_3D_KEY) {
                setSurfaceLabel('SATELLITE IMAGERY · CESIUM WORLD ELEVATION');
                statusRef.current('terrain');
              }
            }
            return;
          } catch (error) {
            console.warn('Cesium World Terrain unavailable; trying public global elevation.', error);
          }
        }
        try {
          const terrain = await ArcGISTiledElevationTerrainProvider.fromUrl(
            'https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer',
          );
          if (!disposed) {
            viewer.terrainProvider = terrain;
            setTerrainRevision(value => value + 1);
            if (!GOOGLE_MAPS_3D_KEY) {
              setSurfaceLabel('SATELLITE IMAGERY · GLOBAL ELEVATION');
              statusRef.current('terrain');
            }
          }
        } catch (error) {
          if (!disposed) {
            console.warn('Global elevation unavailable; retaining the satellite imagery on the ellipsoid.', error);
            if (!GOOGLE_MAPS_3D_KEY) {
              setSurfaceLabel('SATELLITE IMAGERY · ELEVATION UNAVAILABLE');
              statusRef.current('satellite');
            }
            setTerrainRevision(value => value + 1);
          }
        }
      };
      void loadTerrain();

      clickHandler = new ScreenSpaceEventHandler(viewer.scene.canvas);
      clickHandler.setInputAction((event: { position: Cartesian2 }) => {
        const picked = viewer.scene.pick(event.position) as { id?: { properties?: { wellId?: { getValue: () => string } } } } | undefined;
        const wellId = picked?.id?.properties?.wellId?.getValue();
        if (wellId) selectionRef.current(wellId);
      }, ScreenSpaceEventType.LEFT_CLICK);

      const googleKey = GOOGLE_MAPS_3D_KEY;
      if (googleKey) {
        void (async () => {
          try {
            const googleTiles = await createGooglePhotorealistic3DTileset({ key: googleKey }, { showCreditsOnScreen: true });
            if (disposed) { googleTiles.destroy(); return; }
            tileset = googleTiles;
            viewer.scene.primitives.add(googleTiles);
            setSurfaceLabel('GOOGLE MAPS · PHOTOREALISTIC 3D');
            statusRef.current('photoreal');
          } catch (error) {
            if (disposed) return;
            console.warn('Google Photorealistic 3D Tiles unavailable; using satellite imagery.', error);
            setSurfaceLabel('SATELLITE IMAGERY · 3D TILES UNAVAILABLE');
            statusRef.current('satellite');
          }
        })();
      } else {
        if (!ION_TOKEN) setSurfaceLabel('SATELLITE IMAGERY · LOADING GLOBAL ELEVATION');
        statusRef.current('satellite');
      }

      const useOfflineFallback = () => {
        if (imageryFailed || disposed) return;
        imageryFailed = true;
        viewer.imageryLayers.removeAll(true);
        setSurfaceLabel('NATURAL EARTH COUNTRY MAP · SATELLITE UNAVAILABLE');
        statusRef.current('fallback');
        fallbackPromise ??= addOfflineCountryBoundaries(viewer).catch(error => {
          if (!disposed) console.warn('Offline country-boundary fallback unavailable.', error);
        });
      };

      void (async () => {
        try {
          const imagery = await ArcGisMapServerImageryProvider.fromUrl(
            'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
            { credit: new Credit('Esri, Maxar, Earthstar Geographics, and the GIS User Community') },
          );
          if (!disposed) {
            imagery.errorEvent.addEventListener((error) => {
              error.retry = false;
              useOfflineFallback();
            });
            viewer.imageryLayers.addImageryProvider(imagery);
          }
        } catch (error) {
          if (disposed) return;
          console.warn('Satellite imagery unavailable; using locally bundled Natural Earth country boundaries.', error);
          useOfflineFallback();
        }
      })();
    } catch (error) {
      setEngineError(error instanceof Error ? error.message : 'Cesium could not initialize in this browser.');
      return;
    }

    return () => {
      disposed = true;
      if (canvas && onWheelZoom) canvas.removeEventListener('wheel', onWheelZoom);
      clickHandler?.destroy();
      if (tileset && viewerRef.current) viewerRef.current.scene.primitives.remove(tileset as never);
      viewerRef.current?.destroy();
      viewerRef.current = null;
    };
  }, [zoomEarth]);

  React.useEffect(() => {
    const viewer = viewerRef.current;
    let cancelled = false;
    setSurfaceElevation(null);
    if (!active || !validLocation(active) || !viewer || viewer.isDestroyed()) {
      setElevationState('unavailable');
      return () => { cancelled = true; };
    }
    const terrain = viewer.terrainProvider;
    if (terrain instanceof EllipsoidTerrainProvider || !terrain.availability) {
      setElevationState('unavailable');
      return () => { cancelled = true; };
    }
    setElevationState('loading');
    void sampleTerrainMostDetailed(terrain, [Cartographic.fromDegrees(active.longitude, active.latitude)])
      .then(points => {
        if (cancelled) return;
        const height = points[0]?.height;
        if (typeof height === 'number' && Number.isFinite(height)) {
          setSurfaceElevation(height);
          setElevationState('available');
        } else setElevationState('unavailable');
      })
      .catch(() => { if (!cancelled) setElevationState('unavailable'); });
    return () => { cancelled = true; };
  }, [active?.well_id, active?.latitude, active?.longitude, terrainRevision]);

  React.useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    const layers = viewer.entities;
    // Radius changes are spatial analysis, so animate the same geodesic
    // boundary users see in the field instead of snapping a new ellipse in.
    const sampleRadius = (now: number) => {
      const tween = radiusTweenRef.current;
      const progress = tween.startedAt === 0 ? 1 : Math.min(1, Math.max(0, (now - tween.startedAt) / 520));
      const eased = 1 - Math.pow(1 - progress, 3);
      return tween.fromMeters + (tween.toMeters - tween.fromMeters) * eased;
    };
    const now = performance.now();
    const fromMeters = sampleRadius(now);
    radiusTweenRef.current = { fromMeters, toMeters: radiusKm * 1000, startedAt: now };
    const pins = layers.values.filter(entity => entity.id.startsWith('nwis-well:'));
    pins.forEach(entity => layers.remove(entity));
    // Surface models are recreated when the radius or selection changes.
    // Remove the previous tier entities first to avoid stale rigs or duplicate
    // EntityCollection IDs accumulating across field interactions.
    const surfaceModels = layers.values.filter(entity => entity.id.startsWith('nwis-surface-model:'));
    surfaceModels.forEach(entity => layers.remove(entity));
    const radiusIds = layers.values.filter(entity => entity.id.startsWith('nwis-radius:'));
    radiusIds.forEach(entity => layers.remove(entity));
    const oldHighlights = layers.values.filter(entity => entity.id.startsWith('nwis-highlight:'));
    oldHighlights.forEach(entity => layers.remove(entity));

    const records = stage === 'global'
      ? wells.filter(validLocation)
      : active ? [active, ...nearbyWells(active, wells, radiusKm).map(entry => entry.well)].filter((well, index, list) => validLocation(well) && list.findIndex(item => item.well_id === well.well_id) === index) : [];

    if (stage === 'field' && !surfaceContext && active && validLocation(active)) {
      layers.add({
        id: `nwis-radius:${active.well_id}`,
        name: `${radiusKm} km surface search radius`,
        position: Cartesian3.fromDegrees(active.longitude, active.latitude, 12),
        ellipse: {
          semiMajorAxis: new CallbackProperty(() => sampleRadius(performance.now()), false),
          semiMinorAxis: new CallbackProperty(() => sampleRadius(performance.now()), false),
          height: 0,
          heightReference: HeightReference.CLAMP_TO_GROUND,
          material: Color.fromCssColorString('#66c5b4').withAlpha(0.12),
          outline: true,
          outlineColor: Color.fromCssColorString('#8bd8c6').withAlpha(0.88),
          outlineWidth: 2,
        },
        label: {
          text: `${radiusKm} KM · SURFACE DISTANCE`,
          font: '12px monospace',
          fillColor: Color.fromCssColorString('#c2e8dd'),
          outlineColor: Color.fromCssColorString('#091217'),
          outlineWidth: 3,
          style: 2,
          pixelOffset: new Cartesian2(0, -34),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });
    }

    // A screen-sized reticle keeps the active location readable at globe
    // scale. It marks the surveyed wellhead coordinate only; it is not a
    // physical pad footprint or an inferred location radius.
    if (active && validLocation(active)) {
      layers.add({
        id: `nwis-highlight:${active.well_id}`,
        name: `${active.well_id} · active wellhead`,
        position: Cartesian3.fromDegrees(active.longitude, active.latitude, 40),
        point: {
          pixelSize: stage === 'global' ? 30 : 28,
          color: Color.TRANSPARENT,
          outlineColor: Color.fromCssColorString('#ff9148').withAlpha(0.95),
          outlineWidth: 2,
          heightReference: HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        properties: { wellId: active.well_id },
      });
    }

    records.forEach(well => {
      const isActive = well.well_id === active?.well_id;
      const isSelected = well.well_id === selectedId;
      const isRanked = dorsIds.includes(well.well_id);
      const distance = active ? haversineKm(active, well) : null;
      const color = isActive ? '#ff9949' : isSelected ? '#87dcc7' : isRanked ? '#d7b277' : '#b7c3c3';
      const status = typeof well.status === 'string' && well.status.trim()
        ? well.status.trim()
        : typeof well.operational_status === 'string' && well.operational_status.trim()
          ? well.operational_status.trim() : 'STATUS UNAVAILABLE';
      const title = stage === 'global'
        ? `${well.well_id}${well.field ? ` · ${well.field}` : ''}`
        : `${well.well_id}${distance == null ? '' : ` · ${formatDistanceKm(distance)} km`}${isRanked ? ` · DORS #${dorsIds.indexOf(well.well_id) + 1}` : ''} · ${status}`;
      const labelText = surfaceContext
        ? ''
        : stage === 'global'
        ? title
        : `${well.well_id}\n${distance == null ? 'DISTANCE UNAVAILABLE' : `${formatDistanceKm(distance)} km`}${isRanked ? ` · DORS #${dorsIds.indexOf(well.well_id) + 1}` : ''}\n${status}`;
      // In the compact surface-overview cutaway, show only one active rig so
      // near-coincident wells do not become a pile of representational assets.
      if (stage === 'field' && (!surfaceContext || isActive)) {
        // Three representational surface tiers. Coordinates and ground height
        // come from the selected provider/terrain; these meshes are never
        // presented as surveyed or historically installed equipment.
        const position = Cartesian3.fromDegrees(well.longitude!, well.latitude!, 0);
        const isVolveOffshore = surfaceContext && isActive && sourceLabel.toLocaleUpperCase().includes('VOLVE');
        const modelUrl = isVolveOffshore
          ? '/models/offshore_surface_rig.glb'
          : isActive ? '/models/active_surface_rig.glb'
          : isSelected ? '/models/selected_surface_wellhead.glb' : '/models/offset_wellhead.glb';
        layers.add({
          id: `nwis-surface-model:${well.well_id}`,
          name: `${well.well_id} · representational ${isActive ? 'active installation' : isSelected ? 'selected wellhead' : 'offset wellhead'}`,
          position,
          orientation: Transforms.headingPitchRollQuaternion(position, new HeadingPitchRoll(0, 0, 0)),
          model: {
            uri: modelUrl,
            scale: 1,
            minimumPixelSize: isActive ? surfaceContext ? 76 : 42 : isSelected ? 31 : 17,
            maximumScale: isActive ? surfaceContext ? 48 : 42 : isSelected ? 28 : 12,
            heightReference: HeightReference.CLAMP_TO_GROUND,
            ...(isActive || isSelected ? {
              silhouetteColor: Color.fromCssColorString(isActive ? '#f0a36a' : '#8bd8c6'),
              silhouetteSize: isActive ? 1.4 : 1.15,
            } : {}),
          },
          properties: { wellId: well.well_id, representational: true },
        });
      }
      layers.add({
        id: `nwis-well:${well.well_id}`,
        name: title,
        position: Cartesian3.fromDegrees(well.longitude!, well.latitude!, isActive ? 32 : 16),
        point: stage === 'global' ? {
          pixelSize: isActive ? 20 : isSelected ? 15 : isRanked ? 12 : 9,
          color: Color.fromCssColorString(color),
          outlineColor: Color.fromCssColorString(isActive ? '#fff0da' : isSelected ? '#d9fff4' : '#0b1419'),
          outlineWidth: isActive || isSelected ? 4 : 2,
          heightReference: HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: isActive || isSelected ? Number.POSITIVE_INFINITY : 0,
          scaleByDistance: new NearFarScalar(100_000, 1, 15_000_000, 0.48),
        } : undefined,
        label: {
          text: labelText,
          font: isActive || isSelected ? 'bold 12px monospace' : '10px monospace',
          fillColor: Color.fromCssColorString(color),
          outlineColor: Color.fromCssColorString('#081117'), outlineWidth: 3,
          // Preserve the real, nearly coincident wellhead coordinates while
          // separating the labels in screen space for legibility.
          style: 2, pixelOffset: new Cartesian2(12, isActive ? -16 : isSelected ? 20 : -8),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          scaleByDistance: new NearFarScalar(100_000, 1, 3_000_000, 0),
        },
        properties: { wellId: well.well_id },
      });
    });
  }, [stage, surfaceContext, sourceLabel, wells, active, radiusKm, selectedId, dorsIds]);

  React.useEffect(() => {
    const viewer = viewerRef.current;
    const selected = selectedId ? wells.find(well => well.well_id === selectedId) : null;
    if (stage !== 'field' || surfaceContext || !viewer || viewer.isDestroyed() || !selected || !validLocation(selected)) return;
    const closeFieldAltitude = Math.max(1_400, Math.min(FIELD_ALTITUDE(radiusKm), radiusKm * 1_800));
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(selected.longitude, selected.latitude, closeFieldAltitude),
      orientation: { heading: 0, pitch: -CesiumMath.PI_OVER_TWO, roll: 0 },
      duration: 1.45,
    });
    setPovView(false);
  }, [stage, surfaceContext, selectedId, wells, radiusKm]);

  React.useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    if (!active || !validLocation(active)) {
      if (stage === 'global') viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(80, 23, 16_000_000), duration: 1.4 });
      return;
    }
    const globalAltitude = 15_000_000;
    const fieldAltitude = FIELD_ALTITUDE(radiusKm);
    const povAltitude = Math.max(620, Math.min(1_450, radiusKm * 165));
    const povPitch = -CesiumMath.toRadians(49);
    const povLatitude = active.latitude + povAltitude / Math.tan(CesiumMath.toRadians(49)) / 110_574;
    const destinationHeight = stage === 'global' ? globalAltitude : stage === 'field' ? surfaceContext ? povAltitude : fieldAltitude : -900;
    const pitch = stage === 'global' || stage === 'field' && !surfaceContext ? -CesiumMath.PI_OVER_TWO : surfaceContext ? povPitch : -CesiumMath.PI_OVER_TWO;
    viewer.scene.screenSpaceCameraController.enableCollisionDetection = stage !== 'subsurface';
    setPovView(false);
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(active.longitude, surfaceContext ? povLatitude : active.latitude, destinationHeight),
      orientation: { heading: surfaceContext ? CesiumMath.PI : 0, pitch, roll: 0 },
      duration: stage === 'subsurface' ? 2.4 : stage === 'field' ? 2.8 : 1.6,
    });
  }, [stage, active?.well_id, radiusKm, surfaceContext]);

  React.useEffect(() => {
    const fit = () => {
      const viewer = viewerRef.current;
      if (!viewer || viewer.isDestroyed()) return;
      if (stage === 'global') viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(active && validLocation(active) ? active.longitude : 80, active && validLocation(active) ? active.latitude : 23, 16_000_000), duration: 1.3 });
      else if (active && validLocation(active) && surfaceContext) {
        const povAltitude = Math.max(620, Math.min(1_450, radiusKm * 165));
        const povPitch = -CesiumMath.toRadians(49);
        const povLatitude = active.latitude + povAltitude / Math.tan(CesiumMath.toRadians(49)) / 110_574;
        viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(active.longitude, povLatitude, povAltitude), orientation: { heading: CesiumMath.PI, pitch: povPitch, roll: 0 }, duration: 1.3 });
      }
      else if (active && validLocation(active)) viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(active.longitude, active.latitude, FIELD_ALTITUDE(radiusKm)), orientation: { heading: 0, pitch: -CesiumMath.PI_OVER_TWO, roll: 0 }, duration: 1.3 });
    };
    window.addEventListener('nwis:fit', fit);
    return () => window.removeEventListener('nwis:fit', fit);
  }, [stage, active, radiusKm, surfaceContext]);

  const flyToActive = () => {
    const viewer = viewerRef.current;
    if (!viewer || !active || !validLocation(active)) return;
    setPovView(false);
    setLocating(true);
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(active.longitude, active.latitude, stage === 'global' ? FIELD_ALTITUDE(radiusKm) * 2.4 : FIELD_ALTITUDE(radiusKm)),
      orientation: { heading: 0, pitch: -CesiumMath.PI_OVER_TWO, roll: 0 }, duration: 2.2,
      complete: () => setLocating(false), cancel: () => setLocating(false),
    });
  };

  const setFieldCamera = async (view: 'plan' | 'pov') => {
    const viewer = viewerRef.current;
    const target = (selectedId ? wells.find(well => well.well_id === selectedId) : null) ?? active;
    if (!viewer || viewer.isDestroyed() || stage !== 'field' || !target || !validLocation(target)) return;
    if (view === 'plan') {
      viewer.camera.flyTo({
        destination: Cartesian3.fromDegrees(target.longitude, target.latitude, FIELD_ALTITUDE(radiusKm)),
        orientation: { heading: 0, pitch: -CesiumMath.PI_OVER_TWO, roll: 0 }, duration: 1.25,
      });
      setPovView(false);
      return;
    }
    // Low oblique field POV: put the camera north of the selected well and aim
    // back toward the actual coordinate. This is camera geometry only; it
    // doesn't add any surface features or elevations to the data.
    const altitude = Math.max(260, Math.min(900, radiusKm * 95));
    const pitch = -CesiumMath.toRadians(52);
    const northOffsetM = altitude / Math.tan(CesiumMath.toRadians(52));
    const cameraLatitude = target.latitude + northOffsetM / 110_574;
    let groundElevation = target.well_id === active?.well_id && elevationState === 'available' ? surfaceElevation ?? 0 : 0;
    try {
      if (viewer.terrainProvider.availability) {
        const sampled = await sampleTerrainMostDetailed(viewer.terrainProvider, [Cartographic.fromDegrees(target.longitude, target.latitude)]);
        if (Number.isFinite(sampled[0]?.height)) groundElevation = sampled[0].height;
      }
    } catch { /* Stay usable over the ellipsoid if terrain sampling is unavailable. */ }
    if (viewer.isDestroyed()) return;
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(target.longitude, cameraLatitude, groundElevation + altitude),
      orientation: { heading: CesiumMath.PI, pitch, roll: 0 }, duration: 1.5,
    });
    setPovView(true);
  };

  if (engineError) return <div className="earth-fallback"><div className="earth-fallback-mark">EARTH VIEW UNAVAILABLE</div><p>{engineError}</p><p>Use the well list to continue to field and subsurface context.</p></div>;

  return <div className={`cesium-earth cesium-stage-${stage} ${ION_TOKEN ? 'ion-enabled' : 'ion-free'}`}>
    <div className="cesium-host" ref={hostRef} aria-label="Interactive Earth and field map" />
    <div className="earth-overlay earth-location-status"><span className="earth-status-dot"/><div><b>{stage === 'global' ? 'EARTH · GEOGRAPHIC CONTEXT' : stage === 'field' ? 'FIELD · SURFACE WELL LOCATIONS' : 'DESCENDING TO WELLHEAD'}</b><small>{stage === 'global' ? `${sourceLabel} · Drag to rotate · scroll to zoom` : active && validLocation(active) ? `${sourceLabel} · ${active.well_id} · ${active.latitude.toFixed(4)}, ${active.longitude.toFixed(4)}` : 'Wellhead coordinates unavailable'}</small></div></div>
    <div className="earth-overlay earth-surface-status"><span>{surfaceLabel}</span>{GOOGLE_MAPS_3D_KEY && <i>Google Maps key is browser-visible; restrict it to this app origin and Maps Tiles API.</i>}</div>
    {surfaceContext && active && <div className="surface-elevation-readout"><small>MAP TERRAIN SAMPLE</small><b>{elevationState === 'loading' ? 'Sampling terrain…' : elevationState === 'available' && surfaceElevation != null ? `${surfaceElevation >= 0 ? '+' : ''}${surfaceElevation.toFixed(1)} m` : 'Unavailable from active terrain'}</b><span>{sourceLabel.toLocaleUpperCase().includes('VOLVE') && surfaceElevation != null && Math.abs(surfaceElevation) < 0.1 ? 'Sea-level sample · wellhead elevation unavailable' : 'Terrain datum · not surveyed wellhead elevation'}</span><span className="surface-radius-readout">SEARCH RADIUS · {radiusKm} KM</span></div>}
    {stage === 'global' && <div className="earth-overlay earth-global-hint"><strong>REAL EARTH</strong><span>Select a located well to fly into its field.</span></div>}
    {stage === 'field' && <div className="earth-overlay earth-field-count"><b>{active ? nearbyWells(active, wells, radiusKm).length + 1 : 0}</b><span>WELLS IN {radiusKm} KM SEARCH</span><small>Actual wellhead distance · locations only</small><small className="earth-elevation-value">SURFACE ELEVATION · {elevationState === 'loading' ? 'SAMPLING TERRAIN' : elevationState === 'available' && surfaceElevation != null ? `${surfaceElevation >= 0 ? '+' : ''}${surfaceElevation.toFixed(1)} m` : 'UNAVAILABLE FROM ACTIVE TERRAIN'}</small><small className="earth-model-caption">WELLHEAD MODEL · REPRESENTATIONAL</small></div>}
    <div className="earth-zoom-controls" role="group" aria-label="Earth zoom controls"><button onClick={() => zoomEarth(1)} aria-label="Zoom in">+</button><button onClick={() => zoomEarth(-1)} aria-label="Zoom out">−</button></div>
    {stage === 'field' && <div className="earth-pov-controls" role="group" aria-label="Field camera view"><button className={povView?'selected':''} onClick={() => setFieldCamera('pov')} aria-pressed={povView}>POV</button><button className={!povView?'selected':''} onClick={() => setFieldCamera('plan')} aria-pressed={!povView}>PLAN</button></div>}
    {active && validLocation(active) && stage !== 'subsurface' && <button className="earth-locate-button" onClick={flyToActive} disabled={locating}><span className="earth-locate-cross">⌖</span>{locating ? 'FLYING TO WELL…' : stage === 'global' ? 'FLY TO ACTIVE WELL' : 'FOCUS ACTIVE WELL'}</button>}
    <div className="earth-transition-wash" aria-hidden="true" />
  </div>;
}
