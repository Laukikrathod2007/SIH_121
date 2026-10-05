/*
 * Live digital well scene. The GLB contains the complete well geometry but
 * no authored animation clips, so this renderer animates its named BHA
 * assemblies along a measured-depth spline and moves the cuttings with them.
 * The file is deliberately dependency-free so the local demo works offline.
 */
(function () {
  "use strict";

  var MAX_MD = 4000;
  var LOOP_S = 20;
  var START_MD = 1400;
  var BHA_NAMES = ["Bit", "Sensor", "Steering", "MWD", "Collar"];
  var PHASES = [
    { key: "sense", until: 8 },
    { key: "detect", until: 10 },
    { key: "predict", until: 14.4 },
    { key: "prevent", until: LOOP_S }
  ];
  var canvas, visual, root, panel, tabs, playBtn, depthReadout, statusText, resetBtn;
  var gl, program, model, trajectory, items = [], nodeWorld = [], animatedDepth = START_MD;
  var elapsed = 0, running = false, inView = false, manuallyPaused = false, lastFrame = 0, lastReadout = -1;
  var yaw = 0.08, pitch = 0.035, cameraDistance = 11.5;
  var dragging = false, lastPointer = null, frameId = 0, reducedMotion = false, lastRender = 0, firstFrameDrawn = false;
  var viewProjLoc, modelLoc, normalLoc, eyeLoc, colorLoc, alphaLoc, metalLoc, roughLoc, highlightLoc;
  var posLoc, normalAttr, indexExt;

  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function smoothstep(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
  function phaseFor(s) { return s < 8 ? 0 : s < 10 ? 1 : s < 14.4 ? 2 : 3; }
  function identity() { return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]); }
  function mul(a, b) {
    var o = new Float32Array(16);
    for (var c = 0; c < 4; c++) for (var r = 0; r < 4; r++) {
      o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
    }
    return o;
  }
  function trs(t, q, s) {
    var x=q[0], y=q[1], z=q[2], w=q[3], x2=x+x, y2=y+y, z2=z+z;
    var xx=x*x2, xy=x*y2, xz=x*z2, yy=y*y2, yz=y*z2, zz=z*z2, wx=w*x2, wy=w*y2, wz=w*z2;
    return new Float32Array([
      (1-(yy+zz))*s[0], (xy+wz)*s[0], (xz-wy)*s[0], 0,
      (xy-wz)*s[1], (1-(xx+zz))*s[1], (yz+wx)*s[1], 0,
      (xz+wy)*s[2], (yz-wx)*s[2], (1-(xx+yy))*s[2], 0,
      t[0], t[1], t[2], 1
    ]);
  }
  function quatMul(a, b) {
    return [a[3]*b[0]+a[0]*b[3]+a[1]*b[2]-a[2]*b[1], a[3]*b[1]-a[0]*b[2]+a[1]*b[3]+a[2]*b[0], a[3]*b[2]+a[0]*b[1]-a[1]*b[0]+a[2]*b[3], a[3]*b[3]-a[0]*b[0]-a[1]*b[1]-a[2]*b[2]];
  }
  function normalized(x, y, z) { var n = Math.hypot(x, y, z) || 1; return [x/n, y/n, z/n]; }
  function perspectiveOrtho(aspect, halfH) {
    var halfW = halfH * aspect, near = 0.1, far = 40;
    return new Float32Array([1/halfW,0,0,0, 0,1/halfH,0,0, 0,0,-2/(far-near),0, 0,0,-(far+near)/(far-near),1]);
  }
  function lookAt(eye, center) {
    var z = normalized(eye[0]-center[0], eye[1]-center[1], eye[2]-center[2]);
    var x = normalized(z[2], 0, -z[0]);
    var y = [z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0]];
    return new Float32Array([x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0, -(x[0]*eye[0]+x[1]*eye[1]+x[2]*eye[2]), -(y[0]*eye[0]+y[1]*eye[1]+y[2]*eye[2]), -(z[0]*eye[0]+z[1]*eye[1]+z[2]*eye[2]),1]);
  }
  function transformPoint(m, p) {
    return [m[0]*p[0]+m[4]*p[1]+m[8]*p[2]+m[12], m[1]*p[0]+m[5]*p[1]+m[9]*p[2]+m[13], m[2]*p[0]+m[6]*p[1]+m[10]*p[2]+m[14]];
  }
  function normalMatrix(m) {
    var a=m[0],b=m[1],c=m[2],d=m[4],e=m[5],f=m[6],g=m[8],h=m[9],i=m[10];
    var A=e*i-f*h, B=f*g-d*i, C=d*h-e*g, det=a*A+b*B+c*C || 1;
    return new Float32Array([A/det,(c*h-b*i)/det,(b*f-c*e)/det, B/det,(a*i-c*g)/det,(c*d-a*f)/det, C/det,(b*g-a*h)/det,(a*e-b*d)/det]);
  }

  function buildTrajectory() {
    var pts = [], i;
    for (i = 0; i <= 80; i++) pts.push([-1.55, 3.58 + (-0.41 - 3.58) * (i / 80), 0]);
    var p0=[-1.55,-0.41,0], p1=[-1.55,-1.40,0], p2=[-0.52,-2.15,0], p3=[0.27,-2.15,0];
    for (i = 1; i <= 80; i++) { var t=i/80, u=1-t; pts.push([u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0], u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1],0]); }
    for (i = 1; i <= 50; i++) pts.push([0.27+(1.97-0.27)*i/50,-2.15,0]);
    var d=[0]; for (i=1;i<pts.length;i++) d[i]=d[i-1]+Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);
    return {points:pts,distance:d,length:d[d.length-1]};
  }
  function pointAt(md) {
    var dist=trajectory.length*clamp(md/MAX_MD,0,1), d=trajectory.distance, pts=trajectory.points, lo=0, hi=d.length-1;
    while (lo+1<hi) { var mid=(lo+hi)>>1; if(d[mid]<dist)lo=mid;else hi=mid; }
    var span=d[hi]-d[lo]||1, t=(dist-d[lo])/span, a=pts[lo], b=pts[hi];
    var tx=b[0]-a[0], ty=b[1]-a[1], n=Math.hypot(tx,ty)||1;
    return {x:a[0]+tx*t,y:a[1]+ty*t,z:a[2]+(b[2]-a[2])*t,tx:tx/n,ty:ty/n,angle:Math.atan2(ty,tx)};
  }
  function depthAt(s) {
    var k=[[0,START_MD],[7.6,2480],[9.6,2820],[14.4,3450],[18,MAX_MD],[LOOP_S,MAX_MD]];
    for(var i=1;i<k.length;i++) if(s<=k[i][0]) { var f=smoothstep(k[i-1][0],k[i][0],s); return k[i-1][1]+(k[i][1]-k[i-1][1])*f; }
    return MAX_MD;
  }
  function getLocal(node, idx, md, spin) {
    if (model.dynamic[idx]) {
      var base=model.nodes[model.bitNode].translation || [1.97,-2.15,0];
      var here=model.nodes[idx].translation || base;
      var offset=(base[0]-here[0])*MAX_MD/trajectory.length;
      var p=pointAt(Math.max(0,md-offset));
      var zq=[0,0,Math.sin(p.angle/2),Math.cos(p.angle/2)];
      var sq=[Math.sin(spin/2),0,0,Math.cos(spin/2)];
      var q=quatMul(zq,sq);
      return trs([p.x,p.y,p.z],q,node.scale||[1,1.45,1.45]);
    }
    if (model.cuttingNodes[idx]!==undefined) {
      var cut=model.cuttingNodes[idx], lag=100+(cut.order/(model.cuttingCount-1||1))*760;
      var cp=pointAt(Math.max(0,md-lag)), nx=cp.ty, ny=-cp.tx;
      var phase=spin*0.7+cut.order*1.71, off=0.15+0.07*Math.sin(phase*1.3);
      var cRot=[0,0,Math.sin(phase/2),Math.cos(phase/2)];
      return trs([cp.x+nx*off,cp.y+ny*off,cut.z],cRot,node.scale||[1,1,1]);
    }
    if (node.matrix) return new Float32Array(node.matrix);
    return trs(node.translation||[0,0,0],node.rotation||[0,0,0,1],node.scale||[1,1,1]);
  }
  function updateWorlds(md, spin) {
    nodeWorld.length=model.nodes.length;
    function visit(idx,parent) {
      var node=model.nodes[idx], local=getLocal(node,idx,md,spin), world=parent?mul(parent,local):local;
      nodeWorld[idx]=world;
      (node.children||[]).forEach(function(child){visit(child,world);});
    }
    (model.scenes[model.scene||0].nodes||[]).forEach(function(idx){visit(idx,null);});
  }

  function accessorData(gltf, binary, accessorIndex) {
    var a=gltf.accessors[accessorIndex], view=gltf.bufferViews[a.bufferView];
    var dims={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT2:4,MAT3:9,MAT4:16}[a.type], types={5120:[Int8Array,1,"getInt8"],5121:[Uint8Array,1,"getUint8"],5122:[Int16Array,2,"getInt16"],5123:[Uint16Array,2,"getUint16"],5125:[Uint32Array,4,"getUint32"],5126:[Float32Array,4,"getFloat32"]};
    var T=types[a.componentType], bytes=T[1], stride=view.byteStride||dims*bytes, start=(view.byteOffset||0)+(a.byteOffset||0), dv=new DataView(binary), out=new T[0](a.count*dims);
    for(var i=0;i<a.count;i++) for(var c=0;c<dims;c++) out[i*dims+c]=dv[T[2]](start+i*stride+c*bytes, true);
    return {data:out,count:a.count,dims:dims,componentType:a.componentType};
  }
  function makeShader(type, source) {
    var sh=gl.createShader(type); gl.shaderSource(sh,source); gl.compileShader(sh);
    if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)||"Shader compile failed");
    return sh;
  }
  function initProgram() {
    var vs="attribute vec3 aPosition; attribute vec3 aNormal; uniform mat4 uViewProj; uniform mat4 uModel; uniform mat3 uNormal; varying vec3 vNormal; varying vec3 vWorld; void main(){ vec4 w=uModel*vec4(aPosition,1.0); vWorld=w.xyz; vNormal=normalize(uNormal*aNormal); gl_Position=uViewProj*w; }";
    var fs="precision mediump float; uniform vec4 uColor; uniform float uMetal; uniform float uRough; uniform float uHighlight; uniform vec3 uEye; varying vec3 vNormal; varying vec3 vWorld; void main(){ vec3 N=normalize(vNormal); vec3 L=normalize(vec3(-0.45,0.68,0.72)); vec3 V=normalize(uEye-vWorld); vec3 H=normalize(L+V); float diff=max(dot(N,L),0.0); float shine=mix(72.0,10.0,clamp(uRough,0.0,1.0)); float spec=pow(max(dot(N,H),0.0),shine)*(0.16+0.5*uMetal); vec3 col=uColor.rgb*(0.38+0.72*diff)+vec3(spec); col=mix(col,vec3(0.85,0.24,0.035),uHighlight*0.48); col=pow(max(col,vec3(0.0)),vec3(0.94)); gl_FragColor=vec4(col,uColor.a); }";
    program=gl.createProgram(); gl.attachShader(program,makeShader(gl.VERTEX_SHADER,vs)); gl.attachShader(program,makeShader(gl.FRAGMENT_SHADER,fs)); gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program)||"Program link failed");
    gl.useProgram(program); posLoc=gl.getAttribLocation(program,"aPosition"); normalAttr=gl.getAttribLocation(program,"aNormal");
    viewProjLoc=gl.getUniformLocation(program,"uViewProj"); modelLoc=gl.getUniformLocation(program,"uModel"); normalLoc=gl.getUniformLocation(program,"uNormal"); eyeLoc=gl.getUniformLocation(program,"uEye"); colorLoc=gl.getUniformLocation(program,"uColor"); metalLoc=gl.getUniformLocation(program,"uMetal"); roughLoc=gl.getUniformLocation(program,"uRough"); highlightLoc=gl.getUniformLocation(program,"uHighlight");
  }
  function materialFor(gltf, index) {
    var m=gltf.materials&&gltf.materials[index]||{}, p=m.pbrMetallicRoughness||{};
    return {color:p.baseColorFactor||[0.72,0.74,0.73,1],metal:p.metallicFactor||0,rough:p.roughnessFactor===undefined?0.72:p.roughnessFactor,alphaMode:m.alphaMode||"OPAQUE",doubleSided:!!m.doubleSided};
  }
  function localCenter(position) {
    var min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];
    for(var i=0;i<position.length;i+=3) for(var a=0;a<3;a++){var v=position[i+a];if(v<min[a])min[a]=v;if(v>max[a])max[a]=v;}
    return [(min[0]+max[0])/2,(min[1]+max[1])/2,(min[2]+max[2])/2];
  }
  function prepareGeometry(gltf,binary) {
    var roots=gltf.scenes[gltf.scene||0].nodes, parents={}, names={}, bitNode=-1, dynamic={}, cuttingNodes={}, cuttingCount=0;
    gltf.nodes.forEach(function(n,i){names[n.name]=i;(n.children||[]).forEach(function(c){parents[c]=i;});if(BHA_NAMES.indexOf(n.name)>=0)dynamic[i]=true;});
    bitNode=names.Bit;
    gltf.nodes.forEach(function(n,i){if(/^Settled formation cutting/.test(n.name||"")){cuttingNodes[i]={order:cuttingCount,z:(n.translation||[0,0,0])[2]||0};cuttingCount++;}});
    var nodeList=roots.slice();
    // Preserve the authored scene hierarchy while assigning animation metadata.
    var nodes=gltf.nodes.map(function(n,i){var c=Object.assign({},n); if(dynamic[i])c._animateBHA=true; if(cuttingNodes[i]!==undefined)c._animateCuttings=true; return c;});
    var buffers=[];
    nodes.forEach(function(node,idx){if(node.mesh===undefined)return;var mesh=gltf.meshes[node.mesh];(mesh.primitives||[]).forEach(function(prim){
      var p=accessorData(gltf,binary,prim.attributes.POSITION), n=prim.attributes.NORMAL!==undefined?accessorData(gltf,binary,prim.attributes.NORMAL):null;
      if(!n){n={data:new Float32Array(p.data.length),count:p.count};}
      var ix=prim.indices!==undefined?accessorData(gltf,binary,prim.indices):{data:new Uint16Array(Array.from({length:p.count},function(_,i){return i;})),componentType:5123};
      var pb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,pb);gl.bufferData(gl.ARRAY_BUFFER,p.data,gl.STATIC_DRAW);
      var nb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,nb);gl.bufferData(gl.ARRAY_BUFFER,n.data,gl.STATIC_DRAW);
      var ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,ix.data,gl.STATIC_DRAW);
      var mat=materialFor(gltf,prim.material); buffers.push({node:idx,pb:pb,nb:nb,ib:ib,count:ix.data.length,indexType:ix.componentType===5125?gl.UNSIGNED_INT:ix.componentType===5123?gl.UNSIGNED_SHORT:gl.UNSIGNED_BYTE,mode:prim.mode===undefined?gl.TRIANGLES:[gl.POINTS,gl.LINES,gl.LINE_LOOP,gl.LINE_STRIP,gl.TRIANGLES,gl.TRIANGLE_STRIP,gl.TRIANGLE_FAN][prim.mode],mat:mat,center:localCenter(p.data),name:node.name||"",doubleSided:mat.doubleSided});
    });});
    return {nodes:nodes,meshes:gltf.meshes,materials:gltf.materials,scenes:gltf.scenes,scene:gltf.scene||0,dynamic:dynamic,bitNode:bitNode,cuttingNodes:cuttingNodes,cuttingCount:cuttingCount,items:buffers,nodeList:nodeList,parents:parents};
  }
  async function loadGLB(url) {
    var response=await fetch(url,{cache:"force-cache"}); if(!response.ok)throw new Error("Model fetch failed: "+response.status);
    var ab=await response.arrayBuffer(), dv=new DataView(ab);
    if(dv.getUint32(0,true)!==0x46546c67)throw new Error("Invalid GLB header");
    var offset=12, json=null, bin=null;
    while(offset+8<=ab.byteLength){var len=dv.getUint32(offset,true),type=dv.getUint32(offset+4,true);offset+=8;if(type===0x4e4f534a)json=JSON.parse(new TextDecoder().decode(new Uint8Array(ab,offset,len)).replace(/\u0000+$/g,""));else if(type===0x004e4942)bin=ab.slice(offset,offset+len);offset+=len;}
    if(!json||!bin)throw new Error("GLB is missing its scene data");
    return prepareGeometry(json,bin);
  }

  function resize() {
    if(!canvas||!gl)return;
    var r=canvas.getBoundingClientRect(), dpr=Math.min(window.devicePixelRatio||1,1.25), w=Math.max(1,Math.round(r.width*dpr)), h=Math.max(1,Math.round(r.height*dpr));
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
  }
  function updateWorldsAndRender(s) {
    if(!model||!gl)return;
    var md=depthAt(s), spin=s*2.7; animatedDepth=md;
    updateWorlds(md,spin);
    resize();
    var aspect=canvas.width/Math.max(1,canvas.height), target=[0.12,0.28,0], eye=[target[0]+Math.sin(yaw)*cameraDistance,target[1]+Math.sin(pitch)*cameraDistance,target[2]+Math.cos(yaw)*cameraDistance];
    var vp=mul(perspectiveOrtho(aspect,3.9),lookAt(eye,target));
    gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);gl.useProgram(program);
    gl.uniformMatrix4fv(viewProjLoc,false,vp);gl.uniform3f(eyeLoc,eye[0],eye[1],eye[2]);
    var opaque=[],transparent=[];
    model.items.forEach(function(it){var w=nodeWorld[it.node];if(!w)return;var c=transformPoint(w,it.center), z=transformPoint(lookAt(eye,target),c)[2];(it.mat.alphaMode==="BLEND"||it.mat.color[3]<0.995?transparent:opaque).push({item:it,world:w,z:z});});
    transparent.sort(function(a,b){return a.z-b.z;});
    function draw(entry,blend){var it=entry.item,m=it.mat;gl.bindBuffer(gl.ARRAY_BUFFER,it.pb);gl.enableVertexAttribArray(posLoc);gl.vertexAttribPointer(posLoc,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ARRAY_BUFFER,it.nb);gl.enableVertexAttribArray(normalAttr);gl.vertexAttribPointer(normalAttr,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.ib);gl.uniformMatrix4fv(modelLoc,false,entry.world);gl.uniformMatrix3fv(normalLoc,false,normalMatrix(entry.world));gl.uniform4f(colorLoc,m.color[0],m.color[1],m.color[2],m.color[3]);gl.uniform1f(metalLoc,m.metal);gl.uniform1f(roughLoc,m.rough);
      var name=it.name.toLowerCase(), highlight=name.indexOf("breakout")>=0?smoothstep(7.6,9.6,s)*(1-smoothstep(14.4,16.6,s)):name.indexOf("loss zone")>=0?smoothstep(7.6,9.6,s):0;gl.uniform1f(highlightLoc,highlight);
      if(blend){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);}else{gl.disable(gl.BLEND);gl.depthMask(true);}
      gl.drawElements(it.mode,it.count,it.indexType,0);
    }
    opaque.forEach(function(e){draw(e,false);});transparent.forEach(function(e){draw(e,true);});gl.depthMask(true);gl.disable(gl.BLEND);
    // A fetched GLB is not proof that the browser has painted it. Mark the
    // renderer ready only after at least one mesh has actually been submitted.
    if(!firstFrameDrawn&&model.items.length){firstFrameDrawn=true;visual.setAttribute("data-twin-3d","ready");if(statusText)statusText.textContent="MODEL READY | DRAG TO ORBIT";}
    if(Math.abs(md-lastReadout)>=8){depthReadout.textContent="BIT "+Math.round(md).toLocaleString()+" FT";lastReadout=md;}
    if(statusText)statusText.textContent=s>=LOOP_S?"4,000 FT · SCENARIO COMPLETE":PHASES[phaseFor(s)].key.toUpperCase()+" · MODEL LIVE";
  }
  function updateAnnotations(s) {
    var idx=phaseFor(s); for(var i=0;i<tabs.length;i++)tabs[i].setAttribute("data-active",i===idx?"true":"false");
    var risk=smoothstep(7.6,9.6,s)*(1-smoothstep(14.4,16.6,s));
    var failure=smoothstep(10.4,12.2,s)*(1-smoothstep(14,16,s));
    var correction=smoothstep(11.4,14.4,s)*(1-smoothstep(18.4,LOOP_S,s));
    var baseline=smoothstep(0,0.8,s);
    function alpha(name,value){var el=root.querySelector('[data-anno="'+name+'"]');if(el)el.style.opacity=String(value);}
    alpha("surface",baseline);alpha("formation",baseline);alpha("bha",baseline);alpha("casing",Math.max(baseline*0.7,risk));alpha("loss",risk);alpha("tight",risk);alpha("risk",risk);alpha("cuttings",Math.max(risk*0.8,correction*0.9));alpha("failure",failure);alpha("correction",correction);
    panel.setAttribute("data-phase",PHASES[idx].key);
  }
  function setButtonState() {
    var icon=playBtn&&playBtn.querySelector("[data-play-icon]"), text=playBtn&&playBtn.querySelector("[data-play-text]");
    if(!playBtn)return;
    var complete=elapsed>=LOOP_S, label=complete?"Replay":running?"Pause":"Play";
    playBtn.setAttribute("aria-label",label+" digital twin animation");
    if(icon)icon.textContent=complete?"↻":running?"Ⅱ":"▷";
    if(text)text.textContent=label;
  }
  function frame(now) {
    if(!lastFrame)lastFrame=now; var dt=Math.min(0.05,(now-lastFrame)/1000);lastFrame=now;
    if(running&&inView&&!reducedMotion)elapsed=Math.min(LOOP_S,elapsed+dt);
    if(inView&&now-lastRender>=33){updateAnnotations(elapsed);updateWorldsAndRender(elapsed);setButtonState();lastRender=now;}
    if(elapsed>=LOOP_S&&running){running=false;setButtonState();}
    frameId=requestAnimationFrame(frame);
  }
  function togglePlay() {
    if(elapsed>=LOOP_S){elapsed=0;lastFrame=0;manuallyPaused=false;}
    else manuallyPaused=!manuallyPaused;
    running=inView&&!manuallyPaused&&elapsed<LOOP_S;
    setButtonState();
  }
  function resetCamera() { yaw=0.08;pitch=0.035;cameraDistance=11.5; }
  function onPointerDown(e){dragging=true;lastPointer=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);}
  function onPointerMove(e){if(!dragging||!lastPointer)return;var dx=e.clientX-lastPointer[0],dy=e.clientY-lastPointer[1];lastPointer=[e.clientX,e.clientY];yaw+=dx*0.008;pitch=clamp(pitch+dy*0.008,-0.8,0.8);}
  function onPointerUp(){dragging=false;lastPointer=null;}
  function onWheel(e){e.preventDefault();cameraDistance=clamp(cameraDistance+e.deltaY*0.008,8,20);}
  function fail(error){console.error("Digital twin 3D:",error);visual.setAttribute("data-twin-3d","error");if(statusText)statusText.textContent="3D UNAVAILABLE | STILL VIEW";canvas.setAttribute("aria-label","Still view of the digital well model. The 3D renderer could not start.");}
  function initGL() {
    gl=canvas.getContext("webgl2",{alpha:true,antialias:true,depth:true,powerPreference:"high-performance"})||canvas.getContext("webgl",{alpha:true,antialias:true,depth:true});
    if(!gl)throw new Error("WebGL is unavailable in this browser");
    if(gl.UNSIGNED_INT===undefined&&gl.getExtension)indexExt=gl.getExtension("OES_element_index_uint");
    initProgram();
  }
  async function init() {
    root=document.getElementById("dw-twin-scene");panel=document.getElementById("dw-twin-panel");
    if(!root||!panel)return;
    visual=root.querySelector(".dw-twin-visual");canvas=root.querySelector("[data-twin-canvas]");tabs=root.parentElement.querySelectorAll("[data-twin-tab]");
    playBtn=document.getElementById("dw-twin-play");depthReadout=root.querySelector("[data-depth-readout]");statusText=root.querySelector("[data-twin-status]");resetBtn=root.querySelector("[data-twin-reset]");
    if(!visual||!canvas||!depthReadout)return;
    reducedMotion=window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if(reducedMotion){elapsed=LOOP_S;running=false;}
    visual.setAttribute("data-twin-3d","loading");
    if(playBtn)playBtn.addEventListener("click",togglePlay);
    if(resetBtn)resetBtn.addEventListener("click",resetCamera);
    canvas.addEventListener("pointerdown",onPointerDown);canvas.addEventListener("pointermove",onPointerMove);canvas.addEventListener("pointerup",onPointerUp);canvas.addEventListener("pointercancel",onPointerUp);canvas.addEventListener("wheel",onWheel,{passive:false});
    canvas.addEventListener("dblclick",resetCamera);window.addEventListener("resize",resize);
    try {
      initGL();trajectory=buildTrajectory();model=await loadGLB("assets/3d-models/well-digital-twin.glb");
      // Paint a deterministic initial frame now. Waiting for IntersectionObserver
      // here can leave a blank canvas when the section is already in view or the
      // observer callback is delayed by a background tab.
      resize();updateAnnotations(elapsed);updateWorldsAndRender(elapsed);
      if("IntersectionObserver" in window){
        var observer=new IntersectionObserver(function(entries){
          var visible=entries.some(function(entry){return entry.isIntersecting&&entry.intersectionRatio>0.08;});
          if(visible&&!inView&&elapsed>=LOOP_S){elapsed=0;lastFrame=0;}
          inView=visible;running=inView&&!manuallyPaused&&elapsed<LOOP_S;lastFrame=0;lastRender=0;setButtonState();
        },{threshold:[0,0.08,0.25]});
        observer.observe(panel);
      }else{inView=true;running=!reducedMotion;}
    }
    catch(error){fail(error);}
    if(reducedMotion){updateAnnotations(LOOP_S);updateWorldsAndRender(LOOP_S);setButtonState();return;}
    frameId=requestAnimationFrame(frame);
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();
