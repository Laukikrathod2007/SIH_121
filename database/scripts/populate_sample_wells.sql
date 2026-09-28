-- ============================================================================
-- Sample Data Population Script
-- Run after database creation to insert 5 offset wells manually
-- ============================================================================

-- Connect to database first:
-- psql -U nwis_app -d nwis_production

-- ============================================================================
-- Insert 5 Offset Wells (Utah FORGE mapped to Assam fields)
-- ============================================================================

INSERT INTO wells (
    well_name, 
    forge_source_id, 
    location, 
    latitude, 
    longitude, 
    field_name, 
    well_status, 
    is_offset_well,
    is_active_well,
    data_source,
    spud_date,
    total_depth_md,
    operator
) VALUES 
-- Well 1: Nahorkatiya (from 56-32)
(
    'NH-001', 
    '56-32', 
    ST_SetSRID(ST_MakePoint(95.33, 27.29), 4326), 
    27.29, 
    95.33, 
    'Nahorkatiya', 
    'completed',
    TRUE,
    FALSE,
    'utah_forge',
    '2021-02-05',
    3000.00,
    'Oil India Limited'
),

-- Well 2: Moran (from 78B-32)
(
    'MR-002', 
    '78B-32', 
    ST_SetSRID(ST_MakePoint(95.16, 27.28), 4326), 
    27.28, 
    95.16, 
    'Moran', 
    'completed',
    TRUE,
    FALSE,
    'utah_forge',
    '2021-01-15',
    2800.00,
    'Oil India Limited'
),

-- Well 3: Digboi - ACTIVE WELL (from 16A(78)-32)
(
    'DG-003', 
    '16A(78)-32', 
    ST_SetSRID(ST_MakePoint(95.62, 27.38), 4326), 
    27.38, 
    95.62, 
    'Digboi', 
    'drilling',
    FALSE,
    TRUE,  -- This is the active well being monitored
    'utah_forge',
    '2020-10-25',
    NULL,  -- Still drilling
    'Oil India Limited'
),

-- Well 4: Baghjan
(
    'BG-004', 
    'well_3', 
    ST_SetSRID(ST_MakePoint(95.45, 27.30), 4326), 
    27.30, 
    95.45, 
    'Baghjan', 
    'completed',
    TRUE,
    FALSE,
    'utah_forge',
    '2020-08-10',
    3200.00,
    'Oil India Limited'
),

-- Well 5: Rudrasagar
(
    'RD-005', 
    'well_4', 
    ST_SetSRID(ST_MakePoint(95.28, 27.25), 4326), 
    27.25, 
    95.28, 
    'Rudrasagar', 
    'completed',
    TRUE,
    FALSE,
    'utah_forge',
    '2020-06-20',
    2900.00,
    'Oil India Limited'
);

-- ============================================================================
-- Verify Wells Were Inserted
-- ============================================================================

SELECT 
    well_name, 
    field_name, 
    well_status,
    is_active_well,
    ST_AsText(location::geometry) AS location_wkt,
    total_depth_md
FROM wells
ORDER BY well_name;

-- ============================================================================
-- Calculate Offset Well Links (distances between wells)
-- ============================================================================

INSERT INTO offset_well_links (well_id_a, well_id_b, distance_km, bearing_deg)
SELECT 
    w1.well_id,
    w2.well_id,
    ROUND((ST_Distance(w1.location, w2.location) / 1000)::numeric, 2) AS distance_km,
    ROUND(degrees(ST_Azimuth(w1.location::geometry, w2.location::geometry))::numeric, 2) AS bearing_deg
FROM wells w1
CROSS JOIN wells w2
WHERE w1.well_id < w2.well_id;

-- ============================================================================
-- Verify Offset Well Links
-- ============================================================================

SELECT 
    w1.well_name AS well_a,
    w2.well_name AS well_b,
    owl.distance_km,
    owl.bearing_deg,
    owl.is_nearby,
    CASE 
        WHEN owl.is_nearby THEN '✓ Within 10km'
        ELSE 'Far offset'
    END AS proximity_status
FROM offset_well_links owl
JOIN wells w1 ON owl.well_id_a = w1.well_id
JOIN wells w2 ON owl.well_id_b = w2.well_id
ORDER BY owl.distance_km;

-- ============================================================================
-- Insert Sample Formation Tops (for visualization testing)
-- ============================================================================

-- Get well IDs for reference
DO $$
DECLARE
    well_dg003 UUID;
    well_nh001 UUID;
BEGIN
    SELECT well_id INTO well_dg003 FROM wells WHERE well_name = 'DG-003';
    SELECT well_id INTO well_nh001 FROM wells WHERE well_name = 'NH-001';
    
    -- Formations for DG-003 (Active Well)
    INSERT INTO formation_tops (
        well_id, formation_name, formation_lithology, 
        top_depth_md, bottom_depth_md, thickness_md,
        top_depth_tvd, formation_age
    ) VALUES 
    (well_dg003, 'Girujan Clay', 'Shale', 100, 400, 300, 100, 'Pliocene'),
    (well_dg003, 'Tipam Sandstone', 'Sandstone', 400, 1200, 800, 395, 'Miocene'),
    (well_dg003, 'Barail Formation', 'Shale/Sandstone', 1200, 2000, 800, 1180, 'Oligocene'),
    (well_dg003, 'Kopili Shale', 'Shale', 2000, 2600, 600, 1960, 'Eocene');
    
    -- Formations for NH-001 (Offset Well)
    INSERT INTO formation_tops (
        well_id, formation_name, formation_lithology, 
        top_depth_md, bottom_depth_md, thickness_md,
        top_depth_tvd, formation_age
    ) VALUES 
    (well_nh001, 'Girujan Clay', 'Shale', 120, 420, 300, 120, 'Pliocene'),
    (well_nh001, 'Tipam Sandstone', 'Sandstone', 420, 1250, 830, 418, 'Miocene'),
    (well_nh001, 'Barail Formation', 'Shale/Sandstone', 1250, 2100, 850, 1232, 'Oligocene'),
    (well_nh001, 'Kopili Shale', 'Shale', 2100, 2700, 600, 2065, 'Eocene');
END $$;

-- ============================================================================
-- Verify Formation Tops
-- ============================================================================

SELECT 
    w.well_name,
    ft.formation_name,
    ft.formation_lithology,
    ft.top_depth_md,
    ft.bottom_depth_md,
    ft.thickness_md
FROM formation_tops ft
JOIN wells w ON ft.well_id = w.well_id
ORDER BY w.well_name, ft.top_depth_md;

-- ============================================================================
-- Summary
-- ============================================================================

SELECT '✅ Sample data inserted successfully!' AS status;

SELECT 
    'Wells' AS table_name,
    COUNT(*) AS row_count
FROM wells
UNION ALL
SELECT 
    'Offset Well Links' AS table_name,
    COUNT(*) AS row_count
FROM offset_well_links
UNION ALL
SELECT 
    'Formation Tops' AS table_name,
    COUNT(*) AS row_count
FROM formation_tops;
