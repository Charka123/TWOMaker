# Tropical Weather Outlook Generator

## Project Overview ##

A web application for creating custom Tropical Weather Outlooks (TWOs) for tropical cyclone basins. The generated products should be similar in structure and appearance to NHC Tropical Weather Outlooks, while supporting custom basins and user-defined disturbances.

## Tech Stack ##

- Backend: Python + Flask
- Frontend: HTML, CSS, JavaScript
- Interactive maps: Leaflet.js
- Map/image generation: Cartopy, Matplotlib, Pillow
- Data/configuration: JSON
- Avoid unnecessary frameworks or databases unless the project grows to require them.

## Core Features ##

Users should be able to:
- Select a predefined basin or define a custom basin.
- Add, edit, move, and remove tropical disturbances.
- Specify disturbance location, description, and formation probabilities.
- Preview disturbances on an interactive map.
- Generate NHC-style Tropical Weather Outlook text.
- Generate a corresponding outlook map/image.
- Export the generated product.

## Architecture ##
- Keep the data model independent from presentation.
- A disturbance should contain meteorological/product data such as coordinates, formation probabilities, and discussion text. The text generator, interactive map, and image generator should consume the same underlying data.
- Keep basin definitions configurable rather than hard-coded.

## Development Guidelines ##
- Prefer simple, readable implementations.
- Keep frontend, product-generation, and geographic logic separated.
- Build features incrementally rather than introducing unnecessary abstractions.
- Validate latitude, longitude, probability, and basin-bound inputs.
- Do not imply that generated products are official NHC or government forecasts.
