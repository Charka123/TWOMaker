const form = document.querySelector('#disturbance-form');
const basin = document.querySelector('#basin');
const list = document.querySelector('#disturbances');
const error = document.querySelector('#error');
const imagePeriod = document.querySelector('#image-period');
const imageButton = document.querySelector('#generate-image');
const imageStatus = document.querySelector('#image-status');
const imageResult = document.querySelector('#image-result');
const imagePreview = document.querySelector('#outlook-image');
const imageDownload = document.querySelector('#download-image');
let imageUrl = null;
let imageRevision = 0;

function invalidateImage() {
  imageRevision += 1;
  imageResult.hidden = true;
  imageStatus.textContent = '';
  imagePreview.removeAttribute('src');
  imageDownload.removeAttribute('href');
  if (imageUrl) URL.revokeObjectURL(imageUrl);
  imageUrl = null;
}
imagePeriod.addEventListener('change', invalidateImage);
basin.addEventListener('change', invalidateImage);
let disturbances = [];
const marking = document.querySelector('#marking-type');
const position = document.querySelector('#x-position');
const markingHelp = document.querySelector('#marking-help');
const markingLabels = Object.fromEntries([...marking.options].map(option => [option.value, option.text]));

function updateMarkingFields() {
  position.hidden = marking.value === 'area_only';
  position.disabled = position.hidden;
  markingHelp.textContent = {
    area_only: 'An area of interest without an X or arrow.',
    x_to_area: 'Place the X outside the area. The arrow will point toward the area’s center.',
    x_in_area: 'Place the X inside the formation area. No arrow is needed.',
  }[marking.value];
}
marking.addEventListener('change', updateMarkingFields);
updateMarkingFields();
const drawing = window.createDrawingMap(form, basin);
imagePeriod.addEventListener('change', () => drawing.show(disturbances, imagePeriod.value));

function render() {
  invalidateImage();
  drawing.show(disturbances, imagePeriod.value);
  list.replaceChildren();
  if (!disturbances.length) {
    const empty = document.createElement('p');
    empty.textContent = 'No disturbances yet.';
    list.append(empty);
  }
  disturbances.forEach((item, index) => {
    const card = document.createElement('article');
    const title = document.createElement('h3');
    title.textContent = item.name;
    const location = document.createElement('p');
    location.textContent = markingLabels[item.marking_type];
    if (item.marking_type !== 'area_only') {
      location.textContent += ` · X: ${item.latitude}°, ${item.longitude}°`;
    }
    const area = document.createElement('p');
    area.textContent = item.area.shape === 'polygon'
      ? `Drawn formation area (${item.area.points.length} vertices).`
      : `${item.area.shape === 'ellipse' ? 'Oval' : 'Rectangular'} formation area: ${item.area.south}° to ${item.area.north}° latitude; ${item.area.west}° to ${item.area.east}° longitude.`;
    if (item.marking_type === 'x_to_area' && item.area.shape !== 'polygon') {
      area.textContent += ` Arrow toward ${(item.area.south + item.area.north) / 2}°, ${(item.area.west + item.area.east) / 2}°.`;
    }
    const description = document.createElement('p');
    description.className = 'description';
    description.textContent = item.description;
    const probabilities = document.createElement('p');
    probabilities.textContent = `Formation probability: ${item.probability_48h}% in 48 hours · ${item.probability_7d}% in 7 days`;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.setAttribute('aria-label', `Remove ${item.name}`);
    remove.addEventListener('click', () => {
      disturbances.splice(index, 1);
      render();
    });
    card.append(title, location, area, description, probabilities, remove);
    list.append(card);
  });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  error.textContent = '';
  const item = Object.fromEntries(new FormData(form));
  item.name = item.name.trim();
  item.description = item.description.trim();
  for (const key of ['probability_48h', 'probability_7d']) {
    item[key] = Number(item[key]);
  }
  item.latitude = item.marking_type === 'area_only' ? null : Number(item.latitude);
  item.longitude = item.marking_type === 'area_only' ? null : Number(item.longitude);
  try {
    item.area = drawing.area();
    if (!item.area) throw new Error('Enter valid area bounds.');
  } catch (failure) {
    error.textContent = failure.message;
    return;
  }
  delete item.area_shape;
  for (const key of ['south', 'north', 'west', 'east']) {
    delete item[key];
  }
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  list.querySelectorAll('button').forEach(button => { button.disabled = true; });
  try {
    const response = await fetch('/api/outlook', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({basin_id: basin.value, disturbances: [...disturbances, item]}),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not add disturbance.');
    disturbances = result.disturbances;
    render();
    form.reset();
    updateMarkingFields();
    drawing.reset();
    form.elements.name.focus();
  } catch (failure) {
    error.textContent = failure.message || 'Could not reach the server. Please try again.';
  } finally {
    submit.disabled = false;
    list.querySelectorAll('button').forEach(button => { button.disabled = false; });
  }
});

imageButton.addEventListener('click', async () => {
  invalidateImage();
  const revision = imageRevision;
  const period = imagePeriod.value;
  imageButton.disabled = true;
  imageStatus.textContent = 'Generating image…';
  try {
    const response = await fetch('/api/outlook/image', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({basin_id: basin.value, disturbances, period}),
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || 'Could not generate image.');
    }
    const blob = await response.blob();
    if (revision !== imageRevision) return;
    imageUrl = URL.createObjectURL(blob);
    imagePreview.src = imageUrl;
    imagePreview.alt = `${basin.selectedOptions[0].text} basin with ${disturbances.length} disturbance markings colored by ${period === '7d' ? '7-day' : '48-hour'} formation probability. Unofficial outlook.`;
    imageDownload.href = imageUrl;
    imageDownload.download = `${basin.value}-${period}-outlook.png`;
    imageResult.hidden = false;
    imageStatus.textContent = 'Image ready.';
  } catch (failure) {
    if (revision === imageRevision) imageStatus.textContent = failure.message || 'Could not generate image. Please try again.';
  } finally {
    imageButton.disabled = false;
  }
});
