/* Leaflet drawing state is separate from the outlook form and product data. */
window.createDrawingMap = function (form, basinSelect) {
  const container = document.querySelector('#drawing-map');
  const status = document.querySelector('#drawing-status');
  const shape = form.elements.area_shape;
  const map = L.map(container, {crs: L.CRS.EPSG4326, minZoom: 1, maxZoom: 8,
    doubleClickZoom: false, zoomSnap: 0.25});
  const draft = L.layerGroup().addTo(map);
  const saved = L.layerGroup().addTo(map);
  let background, bounds, mode = 'pan', points = [], complete = false, tracing = false;
  let lastPixel, pointerId;
  let savedItems = [], savedPeriod = '7d';
  const fields = ['south', 'north', 'west', 'east'];
  const tools = [...document.querySelectorAll('[data-draw]')];

  function setMode(value) {
    mode = value;
    map.dragging[value === 'pan' ? 'enable' : 'disable']();
    map.touchZoom[value === 'pan' ? 'enable' : 'disable']();
    map.scrollWheelZoom[value === 'pan' ? 'enable' : 'disable']();
    container.classList.toggle('drawing-active', value !== 'pan');
    tools.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.draw === value)));
  }
  function syncFields() {
    fields.forEach(key => { form.elements[key].disabled = shape.value === 'polygon'; });
  }
  function areaPoints(area) {
    if (area.shape === 'polygon') return area.points;
    const {south:s, north:n, west:w, east:e} = area;
    if (area.shape === 'rectangle') return [[s,w],[n,w],[n,e],[s,e]];
    return Array.from({length: 96}, (_,i) => {
      const angle = i / 96 * 2 * Math.PI;
      return [(s+n)/2 + (n-s)/2*Math.sin(angle), (w+e)/2 + (e-w)/2*Math.cos(angle)];
    });
  }
  function numericArea() {
    if (fields.some(key => form.elements[key].value === '')) return null;
    const area = Object.fromEntries(fields.map(key => [key, Number(form.elements[key].value)]));
    return area.south < area.north && area.west < area.east ? {...area, shape:shape.value} : null;
  }
  function drawX(group, latitude, longitude, color) {
    const p = map.latLngToLayerPoint([latitude, longitude]);
    for (const sign of [-1,1]) {
      L.polyline([map.layerPointToLatLng([p.x-7,p.y-sign*7]),
        map.layerPointToLatLng([p.x+7,p.y+sign*7])], {color, weight:3, interactive:false}).addTo(group);
    }
  }
  function center(area) {
    if (area.shape !== 'polygon') return [(area.south+area.north)/2, (area.west+area.east)/2];
    const levels = [...new Set(area.points.map(p => p[0]))].sort((a,b) => a-b);
    let best = [levels[0], levels[1]];
    for (let i=1; i<levels.length-1; i++) {
      if (levels[i+1]-levels[i] > best[1]-best[0]) best = [levels[i],levels[i+1]];
    }
    const lat = (best[0]+best[1])/2, crossings = [];
    area.points.forEach((a,i) => {
      const b = area.points[(i+1)%area.points.length];
      if ((a[0]>lat) !== (b[0]>lat)) crossings.push(a[1]+(lat-a[0])*(b[1]-a[1])/(b[0]-a[0]));
    });
    crossings.sort((a,b) => a-b);
    let widest = [crossings[0],crossings[1]];
    for (let i=2; i<crossings.length; i+=2) {
      if (crossings[i+1]-crossings[i] > widest[1]-widest[0]) widest = [crossings[i],crossings[i+1]];
    }
    return [lat,(widest[0]+widest[1])/2];
  }
  function show(items, period) {
    savedItems = items; savedPeriod = period; saved.clearLayers();
    items.forEach(item => {
      const probability = item[`probability_${period}`];
      const color = probability < 40 ? '#FFFF00' : probability <= 60 ? '#FF6A00' : '#FF0202';
      const tooltip = document.createElement('span'); tooltip.textContent = item.name;
      L.polygon(areaPoints(item.area), {color, weight:3, fillOpacity:.08}).bindTooltip(tooltip).addTo(saved);
      if (item.marking_type === 'x_to_area') {
        const target = center(item.area), start = [item.latitude,item.longitude];
        L.polyline([start,target],{color,weight:3,interactive:false}).addTo(saved);
        const a=map.latLngToLayerPoint(start), b=map.latLngToLayerPoint(target);
        const length=Math.hypot(b.x-a.x,b.y-a.y), ux=(b.x-a.x)/length, uy=(b.y-a.y)/length;
        const size=Math.min(12,length*.4);
        L.polygon([b, L.point(b.x-ux*size-uy*size/2,b.y-uy*size+ux*size/2),
          L.point(b.x-ux*size+uy*size/2,b.y-uy*size-ux*size/2)].map(p=>map.layerPointToLatLng(p)),
        {color,fillOpacity:1,weight:1,interactive:false}).addTo(saved);
      }
      if (item.latitude !== null) drawX(saved, item.latitude, item.longitude, color);
    });
  }
  function redraw() {
    draft.clearLayers();
    if (shape.value === 'polygon') {
      if (points.length) (complete ? L.polygon : L.polyline)(points,
        {color:'#00e5ff', weight:3, fillOpacity:0.12, interactive:false}).addTo(draft);
    } else {
      const area = numericArea();
      if (area) L.polygon(areaPoints(area), {color:'#00e5ff', weight:3, fillOpacity:0.12, interactive:false}).addTo(draft);
    }
    if (form.elements.marking_type.value !== 'area_only' && form.elements.latitude.value !== '' && form.elements.longitude.value !== '') {
      drawX(draft, Number(form.elements.latitude.value), Number(form.elements.longitude.value), '#00e5ff');
    }
    syncFields();
  }
  function start() {
    points = []; complete = false; shape.value = 'polygon'; redraw();
  }
  function add(latlng) {
    if (!bounds.contains(latlng)) {
      status.textContent = 'Keep the outline inside the basin.'; return;
    }
    if (points.length >= 500) {
      status.textContent = 'Maximum 500 points reached. Finish or redraw a smaller outline.'; return;
    }
    const point = [Number(latlng.lat.toFixed(5)), Number(latlng.lng.toFixed(5))];
    if (!points.length || String(points[points.length-1]) !== String(point)) points.push(point);
    redraw();
  }
  function finish() {
    if (points.length < 3) { status.textContent = 'Draw at least three points enclosing an area.'; return; }
    complete = true; setMode('pan'); redraw();
    status.textContent = `Outline ready (${points.length} points). Add the disturbance to validate and save it.`;
  }
  tools.forEach(button => button.addEventListener('click', () => {
    const value = button.dataset.draw;
    if (value === 'x' && form.elements.marking_type.value === 'area_only') {
      status.textContent = 'Select a marking type with an X first.'; return;
    }
    if (value === 'polygon' || value === 'freehand') start();
    setMode(value);
    status.textContent = {pan:'Drag to pan; use the zoom controls to zoom.',
      freehand:'Press and drag to trace an outline. Release to close it.',
      polygon:'Click around the outline, then choose Finish polygon.',
      x:'Click the current disturbance position.'}[value];
  }));
  map.on('click', event => {
    if (mode === 'polygon') add(event.latlng);
    if (mode === 'x') {
      if (!bounds.contains(event.latlng)) { status.textContent = 'Place the X inside the basin.'; return; }
      form.elements.latitude.value = event.latlng.lat.toFixed(5);
      form.elements.longitude.value = event.latlng.lng.toFixed(5);
      setMode('pan'); redraw(); status.textContent = 'X position updated.';
    }
  });
  container.addEventListener('pointerdown', event => {
    if (mode !== 'freehand' || event.button !== 0 || event.target.closest('.leaflet-control')) return;
    event.preventDefault(); event.stopPropagation();
    start(); tracing = true; pointerId = event.pointerId; lastPixel = [event.clientX,event.clientY];
    container.setPointerCapture(pointerId); add(map.mouseEventToLatLng(event));
  });
  container.addEventListener('pointermove', event => {
    if (!tracing || event.pointerId !== pointerId) return;
    event.preventDefault();
    if (Math.hypot(event.clientX-lastPixel[0],event.clientY-lastPixel[1]) < 4) return;
    lastPixel = [event.clientX,event.clientY]; add(map.mouseEventToLatLng(event));
  });
  container.addEventListener('pointerup', event => {
    if (!tracing || event.pointerId !== pointerId) return;
    tracing = false; container.releasePointerCapture(pointerId); finish();
  });
  container.addEventListener('pointercancel', () => {
    tracing = false; complete = false; setMode('pan');
    status.textContent = 'Drawing interrupted. Redraw the outline.';
  });
  document.querySelector('#finish-drawing').addEventListener('click', finish);
  document.querySelector('#undo-drawing').addEventListener('click', () => {
    points.pop(); complete = false; shape.value = 'polygon'; setMode('polygon'); redraw();
    status.textContent = 'Last point removed. Continue clicking or finish the polygon.';
  });
  function clear() {
    points = []; complete = false; setMode('pan'); redraw();
    status.textContent = 'Choose Freehand and drag to trace an area, or Polygon and click its vertices.';
  }
  document.querySelector('#clear-drawing').addEventListener('click', () => {
    clear(); status.textContent = 'Drawing cleared.';
  });
  shape.addEventListener('change', () => { setMode('pan'); redraw(); });
  form.addEventListener('input', redraw);
  form.addEventListener('change', redraw);
  function loadBasin() {
    const data = basinSelect.selectedOptions[0].dataset;
    bounds = L.latLngBounds([Number(data.south),Number(data.west)], [Number(data.north),Number(data.east)]);
    if (background) map.removeLayer(background);
    background = L.imageOverlay(`/api/basins/${encodeURIComponent(basinSelect.value)}/image`, bounds,
      {attribution:'Natural Earth', alt:'Basin coastlines, borders, lakes and coordinate grid'}).addTo(map);
    background.on('error', () => { status.textContent = 'Basemap could not load. Refresh after checking the Flask server.'; });
    background.bringToBack(); map.setMaxBounds(bounds.pad(.1)); map.fitBounds(bounds);
    clear();
  }
  basinSelect.addEventListener('change', loadBasin);
  map.on('zoomend', () => { redraw(); show(savedItems, savedPeriod); });
  loadBasin();
  new ResizeObserver(() => map.invalidateSize()).observe(container);
  return {
    area() {
      if (shape.value !== 'polygon') return numericArea();
      if (!complete) throw new Error('Finish drawing an area before adding the disturbance.');
      return {shape:'polygon', points:points.map(point => [...point])};
    },
    reset: clear,
    show,
  };
};
