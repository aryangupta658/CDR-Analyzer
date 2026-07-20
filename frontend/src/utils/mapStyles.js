
function createRasterStyle({ tiles, attribution, maxzoom = 19 }) {
  return {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles,
        tileSize: 256,
        maxzoom,
        attribution,
      },
    },
    layers: [
      {
        id: "basemap",
        type: "raster",
        source: "basemap",
        minzoom: 0,
        maxzoom,
        paint: {
          "raster-opacity": 1,
          "raster-resampling": "linear",
        },
      },
    ],
  };
}

export const CDR_MAP_STYLES = {
  light: {
    label: "Light",
    style: createRasterStyle({
      tiles: [
        "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
      ],
      attribution:
        "&copy; OpenStreetMap contributors &copy; CARTO",
    }),
  },

  satellite: {
    label: "Satellite",
    style: createRasterStyle({
      tiles: [
        "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      attribution:
        "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    }),
  },

  topographic: {
    label: "Topographic",
    style: createRasterStyle({
      tiles: [
        "https://tile.opentopomap.org/{z}/{x}/{y}.png",
      ],
      attribution:
        "Map data &copy; OpenStreetMap contributors, SRTM | Map style &copy; OpenTopoMap (CC-BY-SA)",
      maxzoom: 17,
    }),
  },

  osm: {
    label: "Street",
    style: createRasterStyle({
      tiles: [
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      ],
      attribution: "&copy; OpenStreetMap contributors",
    }),
  },
};

export const DEFAULT_CDR_MAP_STYLE = "light";
