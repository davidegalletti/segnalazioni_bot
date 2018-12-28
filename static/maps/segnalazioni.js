var map = new L.Map('map', {
  center: new L.LatLng(41.7, 12.0),
  minZoom: 3,
  zoom: 6
});

// create a new tile layer; cycle, landscape, outdoors, ...
//    https://mc.bbbike.org/mc/?num=2&mt0=mapnik&mt1=hillshading  vedi OSM Hike&Bike
//    map1.eu è molto bella ma incompleta
var tileUrl = 'https://{s}.tile.thunderforest.com/outdoors/{z}/{x}/{y}.png?apikey=0d2b2c10fb3f455e967a7298ff736228',
layer = new L.TileLayer(tileUrl, {
    maxZoom: 18,
    attribution: 'Data &copy; <a href="http://osm.org/copyright" title="OpenStreetMap" target="_blank">OpenStreetMap</a> contributors | Maps &copy; <a href="http://www.thunderforest.com/" title="Thunderforest" target="_blank">Thunderforest</a>',
    });

// add the layer to the map
map.addLayer(layer);


var myURL = jQuery( 'script[src$="segnalazioni.js"]' ).attr( 'src' ).replace( 'segnalazioni.js', '' );

var myIcon = L.icon({
    iconUrl: myURL + 'images/pin24.png',
    iconRetinaUrl: myURL + 'images/pin48.png',
    iconSize: [29, 24],
    iconAnchor: [9, 21],
    popupAnchor: [0, -14]
});
/*
for ( var i=0; i < markers.length; ++i ) 
{
   L.marker( [markers[i].lat, markers[i].lng], {icon: myIcon} )
      .bindPopup( '<a target="_blank" href="/static/' + markers[i].hires + '"/><img src="/static/' + markers[i].thumb + '"/></a><br>' + markers[i].when + ' ' + markers[i].caption )
      .addTo( map );
}
*/
var clusteredMarkers = L.markerClusterGroup();

for ( var i=0; i < markers.length; ++i ) {
    var a = markers[i];
    var title = '<a target="_blank" href="/static/' + markers[i].hires + '"/><img src="/static/' + markers[i].thumb + '"/></a><br>' + markers[i].when + ' ' + markers[i].caption;
    var marker = L.marker(new L.LatLng(markers[i].lat, markers[i].lng), { title: title });
    marker.bindPopup(title);
    clusteredMarkers.addLayer(marker);
}

map.addLayer(clusteredMarkers);
