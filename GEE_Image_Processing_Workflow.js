// GEE java script workflow
// MNDWI - Modified Normalized Difference Water Index
// Landsat 5 & 7 (Green = B2, SWIR1 = B5)
function mndwiLS57(img) {
  var mndwi = img.normalizedDifference(['SR_B2', 'SR_B5']).rename('MNDWI');
  return mndwi.copyProperties(img, ['system:time_start']);
}

// Landsat 8 & 9 (Green = B3, SWIR1 = B6)
function mndwiLS89(img) {
  var mndwi = img.normalizedDifference(['SR_B3', 'SR_B6']).rename('MNDWI');
  return mndwi.copyProperties(img, ['system:time_start']);
}

var ls5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
  .filterBounds(sharkIsland)
  .filter(ee.Filter.lt('CLOUD_COVER', 20))
  .map(mndwiLS57);

var ls7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
  .filterBounds(sharkIsland)
  .filter(ee.Filter.lt('CLOUD_COVER', 20))
  .map(mndwiLS57);

var ls8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
  .filterBounds(sharkIsland)
  .filter(ee.Filter.lt('CLOUD_COVER', 20))
  .map(mndwiLS89);

var ls9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
  .filterBounds(sharkIsland)
  .filter(ee.Filter.lt('CLOUD_COVER', 20))
  .map(mndwiLS89);

// Merge all Landsat
var landsatAll = ls5.merge(ls7).merge(ls8).merge(ls9);

// MNDWI function for Sentinel-2 
function mndwiSentinel(img) {
  // Green = B3, SWIR1 = B11
  var mndwi = img.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  return mndwi.copyProperties(img, ['system:time_start']);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(sharkIsland)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(mndwiSentinel);

// Compute Mean MNDWI for each image 
var combined = landsatAll.merge(s2);

var timeSeries = combined.map(function(img) {
  var mean = img.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: sharkIsland,
    scale: 30,        // use 10 for Sentinel-2 if you want finer detail
    maxPixels: 1e9
  });
  return ee.Feature(null, {
    'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
    'MNDWI': mean.get('MNDWI')
  });
});

// Create island extent as polygon 
var islandPolygons = combined.map(function(img) {
  var date = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd');
  
  // Threshold MNDWI — pixels below 0 are exposed land/sand
  var exposed = img.lt(0).selfMask();
  
  // Vectorize the exposed pixels into polygons
  var vectors = exposed.reduceToVectors({
    geometry: sharkIsland,
    scale: 10,
    geometryType: 'polygon',
    eightConnected: false,
    labelProperty: 'exposed',
    maxPixels: 1e9
  });
  
  // Tag each polygon with its date and mean MNDWI
  var meanMNDWI = img.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: sharkIsland,
    scale: 10,
    maxPixels: 1e9
  }).get('MNDWI');
  
  return vectors.map(function(f) {
    return f.set({
      'date': date,
      'mean_MNDWI': meanMNDWI,
      'tide_height': img.get('tide_height')
    });
  });
}).flatten();

// Print chart to Console panel
var chart = ui.Chart.feature.byFeature(timeSeries, 'date', 'MNDWI')
  .setChartType('ScatterChart')
  .setOptions({
    title: 'MNDWI Time Series — Shark Island (Cape Lookout National Seashore)',
    hAxis: {title: 'Date'},
    vAxis: {title: 'MNDWI', viewWindow: {min: -1, max: 1}},
    pointSize: 3,
    trendlines: {0: {type: 'linear', color: 'red'}}
  });

print(chart);

// Visually check work on a specific date
var singleDate = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(sharkIsland)
  .filterDate('2022-06-01', '2022-06-30')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
  .first();

var mndwiVis = singleDate.normalizedDifference(['B3', 'B11']);

Map.centerObject(sharkIsland, 14);
Map.addLayer(mndwiVis, {min: -0.5, max: 0.5, palette: ['brown', 'white', 'blue']}, 'MNDWI');
Map.addLayer(sharkIsland, {color: 'red'}, 'AOI');

// Export table to do further analysis in ArcGIS Pro
Export.table.toDrive({
  collection: islandPolygons,
  description: 'SharkIsland_Extents_TimeSeries',
  fileFormat: 'SHP'
});

// Exporting specific instances in Shark Island's emergence
var exportDates = [
  '2003-06-15',  // pre-Isabel
  '2004-06-15',  // post-Isabel
  '2010-06-15',  // mid period
  '2015-06-15',  // Sentinel-2 era begins
  '2020-06-15',  // recent
  '2024-06-15'   // most recent
];

// Loop through dates and export each MNDWI image
exportDates.forEach(function(dateStr) {
  var start = ee.Date(dateStr);
  var end = start.advance(3, 'month');
  
  // Get best available image near this date
  // Try Sentinel-2 first for post-2015 dates, fall back to Landsat
  var img = combined
    .filterDate(start, end)
    .first();
  
  // Export at 10m resolution clipped to a buffer around your AOI
  Export.image.toDrive({
    image: img.clip(sharkIsland.buffer(500)), // 500m buffer for context
    description: 'MNDWI_' + dateStr,
    scale: 10,
    region: sharkIsland.buffer(500),
    crs: 'EPSG:4326',
    fileFormat: 'GeoTIFF',
    maxPixels: 1e9
  });
});