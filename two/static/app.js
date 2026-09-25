const form = document.querySelector('#disturbance-form');
const basin = document.querySelector('#basin');
const list = document.querySelector('#disturbances');
const error = document.querySelector('#error');
let disturbances = [];

function render() {
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
    location.textContent = `Latitude: ${item.latitude}° · Longitude: ${item.longitude}°`;
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
    card.append(title, location, description, probabilities, remove);
    list.append(card);
  });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  error.textContent = '';
  const item = Object.fromEntries(new FormData(form));
  item.name = item.name.trim();
  item.description = item.description.trim();
  for (const key of ['latitude', 'longitude', 'probability_48h', 'probability_7d']) {
    item[key] = Number(item[key]);
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
    form.elements.name.focus();
  } catch (failure) {
    error.textContent = failure.message || 'Could not reach the server. Please try again.';
  } finally {
    submit.disabled = false;
    list.querySelectorAll('button').forEach(button => { button.disabled = false; });
  }
});
