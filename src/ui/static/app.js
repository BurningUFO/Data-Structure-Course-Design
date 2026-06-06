const MAP_WIDTH = 1000;
const MAP_HEIGHT = 720;
const MAP_PADDING = 88;
const MAP_MIN_SCALE = 0.75;
const MAP_MAX_SCALE = 4;
const MAP_ZOOM_STEP = 0.0016;
const PRIORITY_METRIC_LIMIT = 4;
const UX_STORAGE_KEY = "tourgraph_ux_state_v1";
const RECENT_SEARCH_LIMIT = 5;
const MATCH_SEPARATOR_PATTERN = /[\s,，。.;；:：、/\\|_\-+()（）\[\]【】{}<>《》"'`~!！?？@#$%^&*=]+/u;
const DEMO_ROUTE_SCENARIOS = {
  single: {
    start_node_id: "gate_north",
    target_node_id: "library",
  },
  multi: {
    start_node_id: "gate_north",
    target_node_ids: ["library", "canteen"],
    return_to_start: true,
  },
};

function createDefaultIndoorState() {
  return {
    buildings: [],
    buildingLookup: {},
    graphLookup: {},
    cache: {},
    activeBuildingId: "",
    activeFloorId: "",
    activePayload: null,
    selectedZoneNodeId: "",
    currentRouteViewId: "",
    mapMode: "outdoor",
    lastIndoorRouteViewId: "",
    loading: null,
    error: "",
  };
}

const state = {
  bootstrap: null,
  activePage: "app",
  activeTab: "route",
  expandedPanel: "",
  expandedPanelElement: null,
  expandedPanelPlaceholder: null,
  currentStartNodeId: "",
  currentUserId: "",
  currentInterests: [],
  focusedNodeId: "",
  nearbyCenterNodeId: "",
  currentResults: [],
  currentQueryType: "",
  currentRoute: null,
  recentSearches: [],
  selectedResultIndex: -1,
  selectedDiaryId: "",
  aigcMode: "template",
  aigcCapabilities: {},
  mapRenderer: "simple_svg",
  mapRenderToken: 0,
  basemapMode: "real_map",
  basemapSourceIndex: 0,
  basemapError: "",
  mapGeoJson: null,
  mapGeoJsonStats: null,
  mapGeoJsonSiteId: "",
  mapGeoJsonLoading: null,
  osmLayers: null,
  osmLayersStats: null,
  osmLayersMetadata: null,
  osmLayersSiteId: "",
  osmLayersLoading: null,
  osmLayerError: "",
  osmLayerVisibility: {
    roads: true,
    buildings: true,
    water_landuse: true,
  },
  whiteRoadRoleVisibility: {
    junction: true,
    bend: true,
    endpoint: true,
    poi_access: true,
  },
  whiteRoadEdgesVisible: true,
  pathNodesVisible: false,
  indoor: createDefaultIndoorState(),
  mapView: {
    scale: 1,
    translateX: 0,
    translateY: 0,
    isPanning: false,
    lastPointerX: 0,
    lastPointerY: 0,
  },
  leaflet: {
    map: null,
    edgeLayer: null,
    nodeLayer: null,
    tileLayer: null,
    tileLayerMode: "",
    tileLayerSourceId: "",
    osmWaterLanduseLayer: null,
    osmBuildingsLayer: null,
    osmRoadsLayer: null,
    osmLayersPayload: null,
    baseGeoJson: null,
    routeLayer: null,
    fittedSiteId: "",
    siteBoundsFitted: false,
  },
};

document.addEventListener("DOMContentLoaded", () => {
  void init();
});

async function init() {
  bindPageShell();
  bindTabSwitching();
  bindForms();

  try {
    await loadSiteBootstrap("");
    applyActiveTabState("route");
    switchPage("home");
    setStatus(
      "从首页进入工作区后，可直接按推荐路径开始答辩演示。",
      "info",
    );
  } catch (error) {
    setStatus(`初始化失败：${error.message}`, "error");
  }
}

async function loadSiteBootstrap(siteId) {
  const query = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  const bootstrap = await apiGet(`/api/bootstrap${query}`);
  state.bootstrap = bootstrap;
  state.mapRenderer = "leaflet_geo";
  state.basemapMode = defaultBasemapMode(bootstrap);
  state.basemapSourceIndex = 0;
  state.basemapError = "";
  state.mapGeoJson = null;
  state.mapGeoJsonStats = null;
  state.mapGeoJsonSiteId = "";
  state.mapGeoJsonLoading = null;
  state.osmLayers = null;
  state.osmLayersStats = null;
  state.osmLayersMetadata = null;
  state.osmLayersSiteId = "";
  state.osmLayersLoading = null;
  state.osmLayerError = "";
  state.osmLayerVisibility = defaultOsmLayerVisibility(bootstrap);
  state.whiteRoadRoleVisibility = defaultWhiteRoadRoleVisibility();
  state.whiteRoadEdgesVisible = true;
  state.pathNodesVisible = false;
  state.indoor = createDefaultIndoorState();
  clearLeafletLayers();
  state.currentStartNodeId = bootstrap.default_start_node;
  hydrateBootstrap(bootstrap);
  resetInteractionState({ clearForms: true });
  restoreUserContext();
  syncUserContextControls();
  if (state.activePage === "app") {
    renderMap();
  }
  return bootstrap;
}

function bindPageShell() {
  document.addEventListener("click", (event) => {
    const tourRunButton = event.target.closest("[data-tour-run-all]");
    if (tourRunButton) {
      void runGuidedTour();
      return;
    }

    const tourStepButton = event.target.closest("[data-tour-step]");
    if (tourStepButton) {
      void runTourStep(tourStepButton.dataset.tourStep || "");
      return;
    }

    const suggestionButton = event.target.closest("[data-empty-suggestion]");
    if (suggestionButton) {
      void runEmptySuggestion(suggestionButton.dataset.emptySuggestion || "");
      return;
    }

    const recentSearchButton = event.target.closest("[data-recent-search]");
    if (recentSearchButton) {
      void runRecentSearch(Number(recentSearchButton.dataset.recentSearch));
      return;
    }

    const pageButton = event.target.closest("[data-page]");
    if (!pageButton) {
      return;
    }

    switchPage(pageButton.dataset.page);
  });

  document.addEventListener("click", (event) => {
    const expandButton = event.target.closest("[data-expand-panel]");
    if (expandButton) {
      togglePanelExpansion(expandButton.dataset.expandPanel);
      return;
    }

    if (event.target.matches("#panel-modal-backdrop")) {
      closeExpandedPanel();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeExpandedPanel();
    }
  });
}

function switchPage(page) {
  if (!page) {
    return;
  }

  state.activePage = page;

  document.querySelectorAll("[data-page]").forEach((item) => {
    item.classList.toggle("active", item.dataset.page === page);
  });

  document.querySelectorAll("[data-page-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.pagePanel === page);
  });

  if (page === "app") {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        renderMap();
      });
    });
  }
}

function togglePanelExpansion(panelName) {
  if (!panelName) {
    return;
  }

  if (state.expandedPanel === panelName) {
    closeExpandedPanel();
    return;
  }

  closeExpandedPanel();
  const panel = document.querySelector(`[data-expandable-panel="${panelName}"]`);
  const backdrop = document.querySelector("#panel-modal-backdrop");
  if (!panel || !backdrop) {
    return;
  }

  state.expandedPanel = panelName;
  state.expandedPanelElement = panel;
  state.expandedPanelPlaceholder = document.createComment(`expanded-panel-${panelName}`);
  panel.parentNode.insertBefore(state.expandedPanelPlaceholder, panel);
  document.body.appendChild(panel);
  panel.classList.add("panel-expanded");
  backdrop.hidden = false;
  document.body.classList.add("modal-open");
  syncExpandButtons(panelName, true);

  if (panelName === "map") {
    refreshMapAfterLayoutChange();
  }
}

function closeExpandedPanel() {
  if (!state.expandedPanel) {
    return;
  }

  const expandedPanelName = state.expandedPanel;
  const expandedPanel = state.expandedPanelElement;
  if (expandedPanel) {
    expandedPanel.classList.remove("panel-expanded");
  }

  if (
    expandedPanel &&
    state.expandedPanelPlaceholder &&
    state.expandedPanelPlaceholder.parentNode
  ) {
    state.expandedPanelPlaceholder.parentNode.insertBefore(
      expandedPanel,
      state.expandedPanelPlaceholder,
    );
    state.expandedPanelPlaceholder.remove();
  }

  const backdrop = document.querySelector("#panel-modal-backdrop");
  if (backdrop) {
    backdrop.hidden = true;
  }

  document.body.classList.remove("modal-open");
  state.expandedPanel = "";
  state.expandedPanelElement = null;
  state.expandedPanelPlaceholder = null;
  syncExpandButtons(expandedPanelName, false);

  if (expandedPanelName === "map") {
    refreshMapAfterLayoutChange();
  }
}

function syncExpandButtons(panelName, isExpanded) {
  document.querySelectorAll(`[data-expand-panel="${panelName}"]`).forEach((button) => {
    const collapsedLabels = {
      control: "展开表单",
      map: "展开大地图",
      result: "展开结果",
    };
    const expandedLabels = {
      control: "还原",
      map: "还原地图",
      result: "还原",
    };
    const collapsedLabel = collapsedLabels[panelName] || "展开";
    const expandedLabel = expandedLabels[panelName] || "还原";
    button.textContent = isExpanded ? expandedLabel : collapsedLabel;
    button.setAttribute("aria-label", isExpanded ? expandedLabel : collapsedLabel);
    button.classList.toggle("active", isExpanded);
  });
}

function refreshMapAfterLayoutChange() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (selectedMapRenderer() === "leaflet_geo") {
        if (!state.leaflet.map) {
          renderMap();
          return;
        }

        invalidateLeafletSize();
        fitLeafletToData();
        syncLeafletRouteLayer();
        syncLeafletCaption();
        syncMapDemoPanel();
        return;
      }

      renderSvgMap();
    });
  });
}

function bindTabSwitching() {
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (!button) {
      return;
    }

    switchTab(button.dataset.tab, { openPage: true });
  });
}

function bindForms() {
  document.querySelector("#scenic-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runQuery("/api/search/scenic", {
      keyword: document.querySelector("#scenic-keyword").value.trim(),
      category: document.querySelector("#scenic-category").value,
      sort_field: document.querySelector("#scenic-sort").value,
      start_node_id: state.currentStartNodeId,
      limit: 6,
      ...buildInterestPayload(),
    });
  });

  document.querySelector("#place-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runQuery("/api/search/places", buildPlaceSearchPayload());
  });

  document.querySelector("#place-center-node").addEventListener("change", (event) => {
    const centerNodeId = event.target.value;
    state.nearbyCenterNodeId = centerNodeId;
    applyNearbyProfile(centerNodeId);
  });

  document.querySelector("#catering-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runQuery("/api/recommend/catering", {
      keyword: document.querySelector("#catering-keyword").value.trim(),
      cuisine: document.querySelector("#catering-cuisine").value.trim(),
      sort_field: document.querySelector("#catering-sort").value,
      start_node_id: state.currentStartNodeId,
      limit: 6,
    });
  });

  document.querySelector("#diary-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runQuery("/api/diaries/fulltext", {
      query: document.querySelector("#diary-query").value.trim(),
      limit: 6,
    });
  });

  document.querySelector("#diary-list-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runQuery("/api/diaries/list", {
      sort_field: document.querySelector("#diary-list-sort").value,
      limit: 6,
      ...buildInterestPayload(),
    });
  });

  document.querySelector("#aigc-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runAigcPreview();
  });

  document.querySelector("#aigc-sample").addEventListener("change", (event) => {
    fillAigcFormFromSample(event.target.value);
  });

  document.querySelectorAll("[data-aigc-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      setAigcMode(button.dataset.aigcMode || "template");
    });
  });

  document.querySelector("#diary-create-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await createDiaryFromForm();
  });

  document.querySelector("#diary-update-button").addEventListener("click", async () => {
    await updateDiaryFromForm();
  });

  document.querySelector("#diary-rate-button").addEventListener("click", async () => {
    await rateDiaryFromForm();
  });

  document.querySelector("#diary-clear-button").addEventListener("click", () => {
    clearDiaryManagementForm();
    setStatus("日记管理表单已清空，当前为新建模式。", "info");
  });

  document.querySelector("#route-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const targetNodeId = document.querySelector("#route-target").value;
    await planRoute(targetNodeId);
  });

  document.querySelector("#multi-route-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const targetNodeIds = selectedValues("#multi-route-targets");
    await planMultiRoute(targetNodeIds);
  });

  document.querySelector("#global-start-node").addEventListener("change", (event) => {
    state.currentStartNodeId = event.target.value;
    if (state.currentRoute) {
      clearRoute();
    }
    updateActiveFeatureCaption();
    persistUserContext();
    setStatus(
      `当前起点已切换为 ${getNodeName(state.currentStartNodeId)}。`,
      "info",
    );
  });

  document.querySelector("#user-selector").addEventListener("change", (event) => {
    applySelectedUser(event.target.value);
    updateActiveFeatureCaption();
    persistUserContext();
    setStatus(currentInterestStatusText(), "info");
  });

  document.querySelector("#interest-tags").addEventListener("change", () => {
    state.currentInterests = readInterestTags();
    updateActiveFeatureCaption();
    persistUserContext();
    setStatus(currentInterestStatusText(), "info");
  });

  document.querySelector("#site-selector").addEventListener("change", async (event) => {
    const selectedSiteId = event.target.value;
    const currentSiteId = state.bootstrap ? state.bootstrap.site.id : selectedSiteId;
    if (selectedSiteId === currentSiteId) {
      resetInteractionState({ clearForms: true });
      setStatus(`当前站点为 ${state.bootstrap.site.name}，页面状态已重置。`, "info");
      return;
    }

    setStatus(feedback("site_switching", "正在切换站点并重置页面状态..."), "loading");
    try {
      const bootstrap = await loadSiteBootstrap(selectedSiteId);
      switchTab("route");
      setStatus(
        `${feedback("site_switched", "站点已切换，页面状态已重置。")} 当前站点：${bootstrap.site.name}。`,
        "success",
      );
    } catch (error) {
      event.target.value = currentSiteId;
      setStatus(`站点切换失败：${error.message}`, "error");
    }
  });

  bindMapInteractions();
  bindMapDemoControls();

  document.querySelector("#results-list").addEventListener("click", async (event) => {
    const detailCloseButton = event.target.closest("[data-close-result-detail]");
    if (detailCloseButton) {
      closeResultDetailDrawer();
      return;
    }

    const diaryEditButton = event.target.closest("[data-diary-edit-id]");
    if (diaryEditButton) {
      loadDiaryIntoForm(diaryEditButton.dataset.diaryEditId);
      return;
    }

    const diaryRateButton = event.target.closest("[data-diary-rate-id]");
    if (diaryRateButton) {
      await rateDiary(diaryRateButton.dataset.diaryRateId, 5);
      return;
    }

    const diaryDeleteButton = event.target.closest("[data-diary-delete-id]");
    if (diaryDeleteButton) {
      await deleteDiary(diaryDeleteButton.dataset.diaryDeleteId);
      return;
    }

    const focusButton = event.target.closest("[data-focus-node]");
    if (focusButton) {
      state.focusedNodeId = focusButton.dataset.focusNode;
      renderMap();
      setStatus(`已在地图中定位 ${getNodeName(state.focusedNodeId)}。`, "info");
      return;
    }

    const nearbyButton = event.target.closest("[data-nearby-center]");
    if (nearbyButton) {
      await runNearbySearch(nearbyButton.dataset.nearbyCenter);
      return;
    }

    const routeButton = event.target.closest("[data-route-target]");
    if (routeButton) {
      await planRoute(routeButton.dataset.routeTarget);
      return;
    }

    const resultCard = event.target.closest("[data-result-index]");
    if (resultCard) {
      selectResultByIndex(Number(resultCard.dataset.resultIndex), { openDetail: true, focusMap: true });
    }
  });

  document.querySelector("#results-list").addEventListener("mouseover", (event) => {
    const resultCard = event.target.closest("[data-result-index]");
    if (resultCard) {
      focusResultMapNode(Number(resultCard.dataset.resultIndex), { transient: true });
    }
  });

  document.querySelector("#results-list").addEventListener("focusin", (event) => {
    const resultCard = event.target.closest("[data-result-index]");
    if (resultCard) {
      focusResultMapNode(Number(resultCard.dataset.resultIndex), { transient: true });
    }
  });

  document.addEventListener("click", async (event) => {
    const detailCloseButton = event.target.closest("[data-close-result-detail]");
    if (detailCloseButton) {
      closeResultDetailDrawer();
      return;
    }

    const detailDrawer = event.target.closest("#result-detail-drawer");
    if (detailDrawer) {
      const focusButton = event.target.closest("[data-focus-node]");
      if (focusButton) {
        state.focusedNodeId = focusButton.dataset.focusNode;
        renderMap();
        setStatus(`已在地图中定位 ${getNodeName(state.focusedNodeId)}。`, "info");
        return;
      }

      const nearbyButton = event.target.closest("[data-nearby-center]");
      if (nearbyButton) {
        await runNearbySearch(nearbyButton.dataset.nearbyCenter);
        return;
      }

      const routeButton = event.target.closest("[data-route-target]");
      if (routeButton) {
        await planRoute(routeButton.dataset.routeTarget);
        return;
      }
    }

    const enterIndoorButton = event.target.closest("[data-enter-indoor]");
    if (enterIndoorButton) {
      const buildingId = enterIndoorButton.dataset.enterIndoor || "";
      const floorId = enterIndoorButton.dataset.indoorFloor || "";
      const targetNodeId = enterIndoorButton.dataset.indoorZoneTarget || "";
      if (buildingId) {
        await enterIndoorNavigation(buildingId, {
          floorId,
          routeViewId: indoorRouteViewId(
            buildingId,
            floorId || indoorBuildingRecord(buildingId)?.default_floor_id || "",
          ),
          selectedZoneNodeId: targetNodeId,
        });
      }
      return;
    }

    const routeViewButton = event.target.closest("[data-route-view]");
    if (routeViewButton) {
      await switchIndoorRouteView(routeViewButton.dataset.routeView || "");
      return;
    }

    const floorButton = event.target.closest("[data-indoor-floor]");
    if (floorButton) {
      await switchIndoorFloor(floorButton.dataset.indoorFloor || "");
      return;
    }

    const zoneRouteButton = event.target.closest("[data-indoor-route-target]");
    if (zoneRouteButton) {
      await planRouteFromIndoorZone(zoneRouteButton.dataset.indoorRouteTarget || "");
      return;
    }

    const planSelectedButton = event.target.closest("[data-plan-indoor-route]");
    if (planSelectedButton) {
      await planSelectedIndoorRoute();
      return;
    }

    const zoneButton = event.target.closest("[data-indoor-zone]");
    if (zoneButton) {
      selectIndoorZone(zoneButton.dataset.indoorZone || "");
      return;
    }

    const focusEntryButton = event.target.closest("[data-indoor-entry-focus]");
    if (focusEntryButton) {
      state.focusedNodeId = focusEntryButton.dataset.indoorEntryFocus || "";
      state.indoor.mapMode = "outdoor";
      if (currentRouteHasView("outdoor")) {
        state.indoor.currentRouteViewId = "outdoor";
      }
      renderIndoorPanel();
      renderMap();
      setStatus(`已在室外地图中定位 ${getNodeName(state.focusedNodeId)}。`, "info");
      return;
    }

    const supportedIndoorButton = event.target.closest("[data-show-supported-indoor]");
    if (supportedIndoorButton) {
      switchTab("route");
      const details = document.querySelector("#indoor-supported-buildings-details");
      if (details) {
        details.open = true;
        details.scrollIntoView({
          block: "nearest",
          behavior: "smooth",
        });
      }
      setStatus("已展开支持室内导航的建筑列表。", "info");
    }
  });
}

function bindMapInteractions() {
  const svg = document.querySelector("#campus-map");
  const resetButton = document.querySelector("#map-reset-view");
  const mapViewToggle = document.querySelector("#map-view-toggle");
  if (!svg) {
    return;
  }

  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    zoomMapAt(event.offsetX, event.offsetY, event.deltaY);
  }, { passive: false });

  svg.addEventListener("click", (event) => {
    const nodeElement = event.target.closest("[data-map-node]");
    if (!nodeElement) {
      return;
    }
    const nodeId = nodeElement.dataset.mapNode || "";
    if (!selectResultByNodeId(nodeId, { openDetail: true, scrollIntoView: true })) {
      state.focusedNodeId = nodeId;
      renderMap();
    }
  });

  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) {
      return;
    }
    state.mapView.isPanning = true;
    state.mapView.lastPointerX = event.clientX;
    state.mapView.lastPointerY = event.clientY;
    svg.classList.add("is-panning");
    svg.setPointerCapture(event.pointerId);
  });

  svg.addEventListener("pointermove", (event) => {
    if (!state.mapView.isPanning) {
      return;
    }
    const dx = event.clientX - state.mapView.lastPointerX;
    const dy = event.clientY - state.mapView.lastPointerY;
    state.mapView.lastPointerX = event.clientX;
    state.mapView.lastPointerY = event.clientY;
    state.mapView.translateX += dx;
    state.mapView.translateY += dy;
    renderMap();
  });

  const stopPanning = (event) => {
    if (!state.mapView.isPanning) {
      return;
    }
    state.mapView.isPanning = false;
    svg.classList.remove("is-panning");
    if (event.pointerId !== undefined && svg.hasPointerCapture(event.pointerId)) {
      svg.releasePointerCapture(event.pointerId);
    }
  };

  svg.addEventListener("pointerup", stopPanning);
  svg.addEventListener("pointercancel", stopPanning);
  svg.addEventListener("pointerleave", stopPanning);

  if (resetButton) {
    resetButton.addEventListener("click", () => {
      const wasIndoorView = selectedMapViewMode() === "indoor";
      resetMapView();
      setStatus(wasIndoorView ? "室内平面图已刷新。" : "校园简图已还原到原始比例。", "info");
    });
  }

  if (mapViewToggle) {
    mapViewToggle.addEventListener("click", () => {
      toggleIndoorOutdoorMapView();
    });
  }
}

function zoomMapAt(offsetX, offsetY, deltaY) {
  const currentScale = state.mapView.scale;
  const zoomFactor = Math.exp(-deltaY * MAP_ZOOM_STEP);
  const nextScale = clamp(currentScale * zoomFactor, MAP_MIN_SCALE, MAP_MAX_SCALE);
  if (nextScale === currentScale) {
    return;
  }

  const svg = document.querySelector("#campus-map");
  const rect = svg.getBoundingClientRect();
  const pointerX = (offsetX / Math.max(rect.width, 1)) * MAP_WIDTH;
  const pointerY = (offsetY / Math.max(rect.height, 1)) * MAP_HEIGHT;
  const mapX = (pointerX - state.mapView.translateX) / currentScale;
  const mapY = (pointerY - state.mapView.translateY) / currentScale;

  state.mapView.scale = nextScale;
  state.mapView.translateX = pointerX - mapX * nextScale;
  state.mapView.translateY = pointerY - mapY * nextScale;
  renderMap();
}

function resetMapView() {
  if (selectedMapViewMode() === "indoor") {
    syncIndoorMapStage();
    setMapRendererVisibility(selectedMapRenderer());
    return;
  }
  resetMapViewState();
  if (selectedMapRenderer() === "leaflet_geo") {
    fitLeafletToData();
  }
  renderMap();
}

function bindMapDemoControls() {
  const rendererControls = document.querySelector("#map-renderer-controls");
  if (rendererControls) {
    rendererControls.addEventListener("click", (event) => {
      const rendererButton = event.target.closest("[data-map-renderer]");
      if (!rendererButton) {
        return;
      }
      switchMapRenderer(rendererButton.dataset.mapRenderer);
    });
  }

  const basemapControls = document.querySelector("#map-basemap-controls");
  if (basemapControls) {
    basemapControls.addEventListener("click", (event) => {
      const basemapButton = event.target.closest("[data-map-basemap]");
      if (!basemapButton) {
        return;
      }
      switchBasemapMode(basemapButton.dataset.mapBasemap);
    });
  }

  const osmLayerControls = document.querySelector("#map-osm-layer-controls");
  if (osmLayerControls) {
    osmLayerControls.addEventListener("click", (event) => {
      const layerButton = event.target.closest("[data-osm-layer]");
      if (!layerButton) {
        return;
      }
      toggleOsmLayer(layerButton.dataset.osmLayer);
    });
  }

  const whiteRoadRoleControls = document.querySelector("#white-road-role-controls");
  if (whiteRoadRoleControls) {
    whiteRoadRoleControls.addEventListener("click", (event) => {
      const roleButton = event.target.closest("[data-white-road-role]");
      if (!roleButton) {
        return;
      }
      toggleWhiteRoadRole(roleButton.dataset.whiteRoadRole);
    });
  }

  const whiteRoadEdgeToggle = document.querySelector("#white-road-edge-toggle");
  if (whiteRoadEdgeToggle) {
    whiteRoadEdgeToggle.addEventListener("change", (event) => {
      state.whiteRoadEdgesVisible = Boolean(event.target.checked);
      refreshLeafletInspectionLayers();
      setStatus(
        state.whiteRoadEdgesVisible ? "白线边已显示。" : "白线边已隐藏，POI 和路线仍可检查。",
        "info",
      );
    });
  }

  const pathNodeToggle = document.querySelector("#path-node-toggle");
  if (pathNodeToggle) {
    pathNodeToggle.addEventListener("change", (event) => {
      togglePathNodeVisibility(Boolean(event.target.checked));
    });
  }

  document.querySelectorAll("[data-demo-action]").forEach((button) => {
    button.addEventListener("click", () => {
      void runMapDemoAction(button.dataset.demoAction || "");
    });
  });

  document.addEventListener("click", (event) => {
    const popupRouteButton = event.target.closest(".leaflet-popup-button[data-route-target]");
    if (popupRouteButton) {
      void planRoute(popupRouteButton.dataset.routeTarget);
      return;
    }

    const popupNearbyButton = event.target.closest(".leaflet-popup-button[data-nearby-center]");
    if (popupNearbyButton) {
      void runNearbySearch(popupNearbyButton.dataset.nearbyCenter);
    }
  });
}

function resetMapViewState() {
  state.mapView.scale = 1;
  state.mapView.translateX = 0;
  state.mapView.translateY = 0;
  state.mapView.isPanning = false;
}

function applyActiveTabState(tab) {
  if (!tab) {
    return;
  }

  state.activeTab = tab;
  document.body.dataset.activeTab = tab;

  document.querySelectorAll("[data-tab]").forEach((item) => {
    item.classList.toggle(
      "active",
      item.dataset.tab === tab,
    );
  });

  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tab);
  });

  updateActiveFeatureCaption();
  updateWorkspaceHeading();
  renderFeatureGrid(state.bootstrap?.navigation || []);
}

function switchTab(tab, options = {}) {
  if (!tab) {
    return;
  }

  applyActiveTabState(tab);

  if (options.openPage !== false) {
    switchPage("app");
  }

  if (tab === "help") {
    setStatus("已打开帮助说明，可按推荐链路完成系统演示。", "info");
  }
}

function resetInteractionState(options = {}) {
  state.currentResults = [];
  state.currentRoute = null;
  state.focusedNodeId = "";
  state.nearbyCenterNodeId = "";
  state.currentStartNodeId = state.bootstrap ? state.bootstrap.default_start_node : "";
  state.selectedResultIndex = -1;
  state.selectedDiaryId = "";
  closeResultDetailDrawer();
  resetMapViewState();

  if (options.clearForms) {
    clearUserInputs();
  }

  renderResults({
    success: true,
    message: "暂无结果",
    total: 0,
    query_type: "idle",
    results: [],
  });
  renderRoute(null);
  updateActiveFeatureCaption();
  updateWorkspaceHeading();
  renderFeatureGrid(state.bootstrap?.navigation || []);
  if (state.activePage === "app") {
    renderMap();
  }
}

function clearUserInputs() {
  [
    "#scenic-keyword",
    "#place-keyword",
    "#catering-keyword",
    "#catering-cuisine",
    "#diary-query",
    "#aigc-image",
    "#aigc-prompt",
  ].forEach((selector) => {
    const element = document.querySelector(selector);
    if (element) {
      element.value = "";
    }
  });

  setSelectValue("#scenic-category", "");
  setSelectValue("#place-category", "");
  setSelectValue("#place-center-node", "");
  setSelectValue("#place-radius", "500");
  setSelectValue("#scenic-sort", "interest");
  setSelectValue("#place-sort", "distance_m");
  setSelectValue("#catering-sort", "distance_m");
  setSelectValue("#diary-list-sort", "interest");
  setSelectValue("#route-target", defaultRouteTargetId());
  setMultipleSelectValues("#multi-route-targets", []);
  setSelectValue("#route-strategy", "shortest_distance");
  setSelectValue("#route-transport", "mixed");
  setSelectValue("#global-start-node", state.currentStartNodeId);
  fillAigcFormFromSample(defaultAigcSampleId());
  clearDiaryManagementForm();
  const returnToStart = document.querySelector("#multi-route-return");
  if (returnToStart) {
    returnToStart.checked = true;
  }
}

function setSelectValue(selector, value) {
  const element = document.querySelector(selector);
  if (!element) {
    return;
  }
  const hasValue = Array.from(element.options).some((option) => option.value === value);
  if (hasValue) {
    element.value = value;
  }
}

function setMultipleSelectValues(selector, values) {
  const selectedValuesSet = new Set(values);
  const element = document.querySelector(selector);
  if (!element) {
    return;
  }
  Array.from(element.options).forEach((option) => {
    option.selected = selectedValuesSet.has(option.value);
  });
}

function selectedValues(selector) {
  const element = document.querySelector(selector);
  if (!element) {
    return [];
  }
  return Array.from(element.selectedOptions).map((option) => option.value);
}

function readInterestTags() {
  const element = document.querySelector("#interest-tags");
  if (!element) {
    return [];
  }
  return element.value
    .replaceAll("，", ",")
    .replaceAll("、", ",")
    .replaceAll("；", ",")
    .replaceAll(";", ",")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildInterestPayload() {
  state.currentInterests = readInterestTags();
  return {
    user_id: state.currentUserId,
    interests: state.currentInterests,
  };
}

function findBootstrapUser(userId) {
  return (state.bootstrap?.users || []).find((item) => item.id === userId) || null;
}

function applySelectedUser(userId) {
  const user = findBootstrapUser(userId) || (state.bootstrap?.users || [])[0] || null;
  state.currentUserId = user ? user.id : "";
  state.currentInterests = user && Array.isArray(user.interests) ? user.interests.slice() : [];
  setSelectValue("#user-selector", state.currentUserId);
  const interestInput = document.querySelector("#interest-tags");
  if (interestInput) {
    interestInput.value = state.currentInterests.join(", ");
  }
}

function syncUserContextControls() {
  setSelectValue("#global-start-node", state.currentStartNodeId);
  setSelectValue("#user-selector", state.currentUserId);
  const interestInput = document.querySelector("#interest-tags");
  if (interestInput) {
    interestInput.value = state.currentInterests.join(", ");
  }
  renderRecentSearches();
}

function currentInterestStatusText() {
  const user = findBootstrapUser(state.currentUserId);
  const userName = user ? user.name : "自定义";
  const interests = state.currentInterests.length ? state.currentInterests.join("、") : "未选择";
  return `当前用户：${userName}；当前兴趣偏好：${interests}。`;
}

function hydrateBootstrap(bootstrap) {
  hydrateIndoorBootstrap(bootstrap);
  document.querySelector("#product-title").textContent = bootstrap.product.name;
  document.querySelector("#product-stage").textContent = bootstrap.product.stage;
  document.querySelector("#hero-title").textContent = `${bootstrap.site.name} 导览演示台`;
  document.querySelector("#hero-description").textContent = [
    bootstrap.site.description,
    "当前答辩重点：路线规划、室内导航、查询结果联动。",
  ]
    .filter(Boolean)
    .join(" ");
  const heroSiteSummary = document.querySelector("#hero-site-summary");
  if (heroSiteSummary) {
    heroSiteSummary.textContent = [
      bootstrap.site.location ? `地点：${bootstrap.site.location}` : "",
      `当前支持 ${bootstrap.stats.route_target_count} 个可规划目标`,
    ]
      .filter(Boolean)
      .join(" · ");
  }

  const statMapNodes = document.querySelector("#stat-map-nodes");
  if (statMapNodes) {
    statMapNodes.textContent = String(bootstrap.map.node_count);
  }
  const statRouteTargets = document.querySelector("#stat-route-targets");
  if (statRouteTargets) {
    statRouteTargets.textContent = String(bootstrap.stats.route_target_count);
  }
  const statDiaries = document.querySelector("#stat-diaries");
  if (statDiaries) {
    statDiaries.textContent = String(bootstrap.stats.diary_count);
  }

  populateSelect(
    document.querySelector("#site-selector"),
    bootstrap.sites.map((item) => ({
      value: item.id,
      label: siteOptionLabel(item),
      disabled: !isSiteFrontendSelectable(item),
    })),
    bootstrap.site.id,
  );

  populateSelect(
    document.querySelector("#global-start-node"),
    bootstrap.start_nodes.map((item) => ({
      value: item.id,
      label: `${item.name} · ${item.category_label}`,
    })),
    bootstrap.default_start_node,
  );

  populateSelect(
    document.querySelector("#user-selector"),
    (bootstrap.users || []).map((item) => ({
      value: item.id,
      label: `${item.name} · ${item.interest_text || "无兴趣标签"}`,
    })),
    bootstrap.default_user_id || bootstrap.users?.[0]?.id || "",
  );
  applySelectedUser(bootstrap.default_user_id || bootstrap.users?.[0]?.id || "");

  const defaultTargetId = defaultRouteTargetId(bootstrap);
  populateSelect(
    document.querySelector("#route-target"),
    bootstrap.route_targets.map((item) => ({
      value: item.id,
      label: routeTargetLabel(item),
    })),
    defaultTargetId,
  );

  populateSelect(
    document.querySelector("#multi-route-targets"),
    bootstrap.route_targets.map((item) => ({
      value: item.id,
      label: routeTargetLabel(item),
    })),
    "",
  );

  const diaryDestinationOptions = [{ value: "", label: "不绑定路线目标" }].concat(
    bootstrap.route_targets.map((item) => ({
      value: item.id,
      label: routeTargetLabel(item),
    })),
  );
  populateSelect(document.querySelector("#diary-destination-node"), diaryDestinationOptions, "");

  populateSelect(
    document.querySelector("#aigc-sample"),
    bootstrap.aigc_samples.map((item) => ({
      value: item.sample_id,
      label: `${item.label} · ${item.output_type}`,
    })),
    defaultAigcSampleId(),
  );

  populateSelect(
    document.querySelector("#aigc-style"),
    bootstrap.controls.aigc_styles.map((item) => ({
      value: item.value,
      label: item.label,
    })),
    bootstrap.aigc_samples[0]?.style || "",
  );

  populateSelect(
    document.querySelector("#route-strategy"),
    bootstrap.controls.route_strategies.map((item) => ({
      value: item.value,
      label: item.label,
    })),
    "shortest_distance",
  );

  populateSelect(
    document.querySelector("#route-transport"),
    bootstrap.controls.transport_modes.map((item) => ({
      value: item.value,
      label: item.label,
    })),
    "mixed",
  );

  const scenicOptions = [{ value: "", label: "不限类别" }].concat(
    bootstrap.controls.scenic_categories.map((item) => ({
      value: item.value,
      label: item.label,
    })),
  );
  populateSelect(document.querySelector("#scenic-category"), scenicOptions, "");

  const placeOptions = [{ value: "", label: "不限类别" }].concat(
    bootstrap.controls.place_categories.map((item) => ({
      value: item.value,
      label: item.label,
    })),
  );
  populateSelect(document.querySelector("#place-category"), placeOptions, "");
  const nearbyCenterOptions = [{ value: "", label: "全校场所" }].concat(
    bootstrap.route_targets.map((item) => ({
      value: item.id,
      label: routeTargetLabel(item),
    })),
  );
  populateSelect(document.querySelector("#place-center-node"), nearbyCenterOptions, "");
  const nearbyRadiusOptions = (bootstrap.controls.nearby_radius_options || [
    { value: 200, label: "200 m" },
    { value: 500, label: "500 m" },
    { value: 800, label: "800 m" },
    { value: 1200, label: "1200 m" },
  ]).map((item) => ({
    value: String(item.value),
    label: item.label,
  }));
  populateSelect(document.querySelector("#place-radius"), nearbyRadiusOptions, "500");

  const sortOptions = bootstrap.controls.sort_options.map((item) => ({
    value: item.value,
    label: item.label,
  }));
  const scenicSortOptions = (bootstrap.controls.scenic_sort_options || bootstrap.controls.sort_options).map((item) => ({
    value: item.value,
    label: item.label,
  }));
  const diarySortOptions = (bootstrap.controls.diary_sort_options || [
    { value: "interest", label: "按兴趣推荐" },
    { value: "heat", label: "按热度" },
    { value: "rating", label: "按评分" },
  ]).map((item) => ({
    value: item.value,
    label: item.label,
  }));
  populateSelect(document.querySelector("#scenic-sort"), scenicSortOptions, "interest");
  populateSelect(document.querySelector("#place-sort"), sortOptions, "distance_m");
  populateSelect(document.querySelector("#catering-sort"), sortOptions, "distance_m");
  populateSelect(document.querySelector("#diary-list-sort"), diarySortOptions, "interest");

  renderPresetButtons("#scenic-presets", bootstrap.presets.scenic, handleScenicPreset);
  renderPresetButtons("#place-presets", bootstrap.presets.place, handlePlacePreset);
  renderPresetButtons("#catering-presets", bootstrap.presets.catering, handleCateringPreset);
  renderPresetButtons("#diary-presets", bootstrap.presets.diary, handleDiaryPreset);
  renderPresetButtons("#aigc-presets", bootstrap.presets.aigc, handleAigcPreset);
  renderPresetButtons("#route-presets", filterRoutePresetsForCurrentSite(bootstrap.presets.route), handleRoutePreset);
  renderPresetButtons(
    "#multi-route-presets",
    filterMultiRoutePresetsForCurrentSite(bootstrap.presets.multi_route),
    handleMultiRoutePreset,
  );
  renderIndoorQuickStart();
  state.aigcCapabilities = bootstrap.aigc_capabilities || {};
  setAigcMode("template");
  syncAigcModeAvailability();
  fillAigcFormFromSample(defaultAigcSampleId());
  renderFeatureGrid(bootstrap.navigation);
  renderDemoTour(bootstrap.demo_tour || []);
  renderHelpPanel(bootstrap.help);
  updateActiveFeatureCaption();
  updateWorkspaceHeading();
}

function restoreUserContext() {
  const stored = readStoredUxState();
  if (!stored) {
    return;
  }

  const startIds = startNodeIdSet();
  if (startIds.has(stored.currentStartNodeId)) {
    state.currentStartNodeId = stored.currentStartNodeId;
  }

  if (findBootstrapUser(stored.currentUserId)) {
    state.currentUserId = stored.currentUserId;
  }
  state.currentInterests = Array.isArray(stored.currentInterests)
    ? stored.currentInterests.filter(Boolean).slice(0, 8)
    : state.currentInterests;
  state.recentSearches = Array.isArray(stored.recentSearches)
    ? stored.recentSearches.slice(0, RECENT_SEARCH_LIMIT)
    : [];
}

function readStoredUxState() {
  try {
    const raw = window.localStorage.getItem(UX_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.siteId !== currentSiteId()) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function persistUserContext() {
  if (!state.bootstrap) {
    return;
  }
  try {
    window.localStorage.setItem(UX_STORAGE_KEY, JSON.stringify({
      siteId: currentSiteId(),
      currentStartNodeId: state.currentStartNodeId,
      currentUserId: state.currentUserId,
      currentInterests: state.currentInterests,
      recentSearches: state.recentSearches,
    }));
  } catch {
    // localStorage may be disabled in some browsers; ignore without breaking the demo.
  }
}

function rememberSearch(label, queryType, payload = {}, endpoint = "") {
  const text = label || searchLabelFromPayload(payload);
  if (!text) {
    return;
  }
  const entry = {
    label: text,
    query_type: queryType || "query",
    endpoint,
    payload,
  };
  state.recentSearches = [
    entry,
    ...state.recentSearches.filter((item) => item.label !== entry.label || item.query_type !== entry.query_type),
  ].slice(0, RECENT_SEARCH_LIMIT);
  persistUserContext();
  renderRecentSearches();
}

function searchLabelFromPayload(payload = {}) {
  const candidates = [
    payload.keyword,
    payload.query,
    payload.cuisine,
    payload.category,
    payload.tag,
    payload.destination,
    payload.title,
  ];
  return candidates.find((value) => typeof value === "string" && value.trim())?.trim() || "";
}

function renderRecentSearches() {
  const container = document.querySelector("#recent-searches");
  if (!container) {
    return;
  }
  const strip = container.closest(".recent-search-strip");
  if (strip) {
    strip.classList.toggle("is-empty", !state.recentSearches.length);
  }
  if (!state.recentSearches.length) {
    container.innerHTML = `<span class="recent-empty">暂无</span>`;
    return;
  }
  container.innerHTML = state.recentSearches
    .map((item, index) => `
      <button class="quick-chip" type="button" data-recent-search="${index}">
        ${escapeHtml(item.label)}
      </button>
    `)
    .join("");
}

async function runRecentSearch(index) {
  const entry = state.recentSearches[index];
  if (!entry) {
    return;
  }
  const tab = tabForQueryType(entry.query_type);
  switchTab(tab, { openPage: true });
  applySuggestionToForm({
    tab,
    payload: entry.payload || {},
  });
  await runQuery(entry.endpoint || endpointForQueryType(entry.query_type), {
    ...(entry.payload || {}),
    start_node_id: state.currentStartNodeId,
    limit: 6,
    ...(tab === "scenic" ? buildInterestPayload() : {}),
  });
}

function tabForQueryType(queryType) {
  if (queryType === "place_search" || queryType === "catering_recommend") {
    return "place";
  }
  if (queryType === "diary_fulltext_search" || queryType === "diary_list") {
    return "diary";
  }
  return "scenic";
}

function endpointForQueryType(queryType) {
  if (queryType === "place_search") {
    return "/api/search/places";
  }
  if (queryType === "catering_recommend") {
    return "/api/recommend/catering";
  }
  if (queryType === "diary_fulltext_search") {
    return "/api/diaries/fulltext";
  }
  return "/api/search/scenic";
}

function siteOptionLabel(site) {
  const pieces = [site.name || site.id, site.location || site.id];
  const statusLabel = siteOptionStatusLabel(site);
  if (statusLabel) {
    pieces.push(statusLabel);
  }
  return pieces.filter(Boolean).join(" · ");
}

function siteOptionStatusLabel(site) {
  if (site?.is_available === false && site?.data_status === "backend_ready") {
    return "试点可演示";
  }
  if (site?.is_available === false) {
    return "待接入";
  }
  return "";
}

function isSiteFrontendSelectable(site) {
  if (!site) {
    return false;
  }
  if (site.is_current || site.is_available !== false) {
    return true;
  }
  return site.data_status === "backend_ready";
}

function routeTargetLabel(item) {
  const pieces = [
    item.name || item.id || "未命名目标",
    item.category_label || item.category || "",
  ];
  if (item.building_name && item.building_name !== item.name) {
    pieces.push(item.building_name);
  }
  if (item.floor_label) {
    pieces.push(item.floor_label);
  }
  return pieces.filter(Boolean).join(" · ");
}

function hydrateIndoorBootstrap(bootstrap) {
  const buildings = Array.isArray(bootstrap?.map_capabilities?.indoor_supported_buildings)
    ? bootstrap.map_capabilities.indoor_supported_buildings
    : Array.isArray(bootstrap?.indoor_buildings)
      ? bootstrap.indoor_buildings
      : [];
  const buildingLookup = {};
  const graphLookup = {};
  buildings.forEach((item) => {
    if (item?.building_id) {
      buildingLookup[item.building_id] = item;
    }
    if (item?.indoor_graph_id) {
      graphLookup[item.indoor_graph_id] = item;
    }
  });
  state.indoor.buildings = buildings;
  state.indoor.buildingLookup = buildingLookup;
  state.indoor.graphLookup = graphLookup;
}

function indoorBuildingRecord(buildingId) {
  return state.indoor.buildingLookup[buildingId] || null;
}

function indoorBuildingByGraph(indoorGraphId) {
  return state.indoor.graphLookup[indoorGraphId] || null;
}

function routeTargetRecord(nodeId) {
  return (state.bootstrap?.route_targets || []).find((item) => item.id === nodeId) || null;
}

function routeTargetIdSet(bootstrap = state.bootstrap) {
  return new Set((bootstrap?.route_targets || []).map((item) => item.id).filter(Boolean));
}

function startNodeIdSet(bootstrap = state.bootstrap) {
  return new Set((bootstrap?.start_nodes || []).map((item) => item.id).filter(Boolean));
}

function defaultRouteTargetId(bootstrap = state.bootstrap) {
  const targets = bootstrap?.route_targets || [];
  const targetIds = routeTargetIdSet(bootstrap);
  const preferredIds = ["library", "second_gate", "canteen"];
  for (const targetId of preferredIds) {
    if (targetIds.has(targetId)) {
      return targetId;
    }
  }
  return targets[0]?.id || "";
}

function filterRoutePresetsForCurrentSite(presets = []) {
  const targetIds = routeTargetIdSet();
  return (presets || []).filter((preset) => targetIds.has(preset.target_node_id));
}

function filterMultiRoutePresetsForCurrentSite(presets = []) {
  const targetIds = routeTargetIdSet();
  return (presets || []).filter((preset) => {
    const presetTargetIds = preset.target_node_ids || [];
    return presetTargetIds.length > 0 && presetTargetIds.every((targetId) => targetIds.has(targetId));
  });
}

function indoorRouteViewId(buildingId, floorId) {
  return buildingId && floorId ? `indoor:${buildingId}:${floorId}` : "";
}

function parseIndoorRouteViewId(viewId) {
  if (!viewId || !viewId.startsWith("indoor:")) {
    return null;
  }
  const [, buildingId, floorId] = viewId.split(":");
  if (!buildingId || !floorId) {
    return null;
  }
  return { buildingId, floorId };
}

function floorLabelForId(floorId) {
  if (typeof floorId !== "string") {
    return "";
  }
  if (/^F\d+$/i.test(floorId)) {
    return `${floorId.slice(1)}F`;
  }
  return floorId;
}

function indoorPayloadFloorId(payload) {
  if (payload?.current_floor?.id) {
    return payload.current_floor.id;
  }
  if (payload?.current_floor_id) {
    return payload.current_floor_id;
  }
  if (typeof payload?.current_floor === "string") {
    return payload.current_floor;
  }
  return "";
}

function indoorPayloadFloorLabel(payload) {
  if (payload?.current_floor?.label) {
    return payload.current_floor.label;
  }
  return floorLabelForId(indoorPayloadFloorId(payload));
}

function indoorPayloadCacheKey(buildingId, floorId) {
  return `${buildingId}:${floorId || ""}`;
}

function isIndoorZoneNode(node) {
  const category = node?.category || "";
  return category !== "passage" && category !== "hall";
}

function findIndoorRouteView(route, buildingId, floorId) {
  const views = route?.ui?.indoor_route_views || [];
  for (const buildingView of views) {
    if (buildingView.building_id !== buildingId) {
      continue;
    }
    for (const floorView of buildingView.floors || []) {
      if (floorView.floor_id === floorId) {
        return { buildingView, floorView };
      }
    }
  }
  return null;
}

function findPrimaryIndoorRouteView(route = state.currentRoute) {
  const views = route?.ui?.indoor_route_views || [];
  for (const buildingView of views) {
    for (const floorView of buildingView.floors || []) {
      if (floorView.contains_target) {
        return { buildingView, floorView };
      }
    }
  }
  if (views[0]?.floors?.[0]) {
    return {
      buildingView: views[0],
      floorView: views[0].floors[0],
    };
  }
  return null;
}

function resolveIndoorContextForTarget(targetNodeId) {
  const target = routeTargetRecord(targetNodeId);
  if (!target) {
    return null;
  }
  const building = target.building_id
    ? indoorBuildingRecord(target.building_id)
    : target.indoor_graph_id
      ? indoorBuildingByGraph(target.indoor_graph_id)
      : target.indoor_supported
        ? indoorBuildingRecord(target.id)
        : null;
  if (!building) {
    return null;
  }
  return {
    buildingId: building.building_id,
    buildingName: target.building_name || building.building_name,
    floorId: target.floor_id || building.default_floor_id || building.floor_ids?.[0] || "",
    floorLabel: target.floor_label || floorLabelForId(target.floor_id || building.default_floor_id || ""),
    targetNodeId,
    targetName: target.name || getNodeName(targetNodeId),
    indoorGraphId: target.indoor_graph_id || building.indoor_graph_id,
    entryNodeId: target.entry_node_id || building.entry_node_id,
  };
}

function resolveIndoorSelectedZoneId(payload, preferredNodeId = "") {
  const zoneIds = new Set((payload?.zones || []).map((item) => item.id));
  if (preferredNodeId && zoneIds.has(preferredNodeId)) {
    return preferredNodeId;
  }
  if (state.currentRoute?.target_node_id && zoneIds.has(state.currentRoute.target_node_id)) {
    return state.currentRoute.target_node_id;
  }
  if (state.indoor.selectedZoneNodeId && zoneIds.has(state.indoor.selectedZoneNodeId)) {
    return state.indoor.selectedZoneNodeId;
  }
  return "";
}

async function loadIndoorPayload(buildingId, floorId) {
  const cacheKey = indoorPayloadCacheKey(buildingId, floorId);
  if (state.indoor.cache[cacheKey]) {
    return state.indoor.cache[cacheKey];
  }

  const query = new URLSearchParams({
    site_id: currentSiteId(),
    building_id: buildingId,
  });
  if (floorId) {
    query.set("floor", floorId);
  }

  const payload = await apiGet(`/api/map/indoor?${query.toString()}`);
  state.indoor.cache[cacheKey] = payload;
  const actualFloorId = indoorPayloadFloorId(payload);
  if (actualFloorId) {
    state.indoor.cache[indoorPayloadCacheKey(buildingId, actualFloorId)] = payload;
  }
  return payload;
}

async function enterIndoorNavigation(buildingId, options = {}) {
  const building = indoorBuildingRecord(buildingId);
  if (!building) {
    state.indoor.error = "当前建筑暂不支持室内导航。";
    renderIndoorPanel();
    if (!options.silentStatus) {
      setStatus("当前建筑暂不支持室内导航。", "error");
    }
    return null;
  }

  switchTab("route");
  const requestedFloorId = options.floorId
    || state.indoor.activeFloorId
    || building.default_floor_id
    || building.floor_ids?.[0]
    || "";
  state.indoor.activeBuildingId = buildingId;
  state.indoor.loading = {
    buildingId,
    floorId: requestedFloorId,
  };
  state.indoor.mapMode = options.routeViewId === "outdoor" ? "outdoor" : "indoor";
  state.indoor.error = "";
  renderIndoorPanel();

  try {
    const payload = await loadIndoorPayload(buildingId, requestedFloorId);
    const activeFloorId = indoorPayloadFloorId(payload) || requestedFloorId;
    const nextRouteViewId = options.routeViewId
      || indoorRouteViewId(buildingId, activeFloorId);
    state.indoor.activeBuildingId = buildingId;
    state.indoor.activeFloorId = activeFloorId;
    state.indoor.activePayload = payload;
    state.indoor.currentRouteViewId = nextRouteViewId;
    if (nextRouteViewId === "outdoor") {
      const rememberedView = parseIndoorRouteViewId(state.indoor.lastIndoorRouteViewId);
      if (rememberedView?.buildingId !== buildingId) {
        state.indoor.lastIndoorRouteViewId = indoorRouteViewId(buildingId, activeFloorId);
      }
      state.indoor.mapMode = "outdoor";
    } else {
      state.indoor.mapMode = "indoor";
      rememberIndoorRouteViewId(nextRouteViewId);
    }
    state.indoor.error = "";
    state.indoor.selectedZoneNodeId = resolveIndoorSelectedZoneId(
      payload,
      options.selectedZoneNodeId || "",
    );
    renderIndoorPanel();
    if (!options.silentStatus) {
      setStatus(
        `已进入 ${building.building_name}${indoorPayloadFloorLabel(payload)} 室内导航。`,
        "info",
      );
    }
    return payload;
  } catch (error) {
    state.indoor.activePayload = null;
    state.indoor.error = `室内地图加载失败：${error.message}`;
    renderIndoorPanel();
    if (!options.silentStatus) {
      setStatus(`室内地图加载失败：${error.message}`, "error");
    }
    return null;
  } finally {
    state.indoor.loading = null;
    renderIndoorPanel();
  }
}

async function switchIndoorFloor(floorId) {
  const buildingId = state.indoor.activeBuildingId;
  if (!buildingId || !floorId) {
    return;
  }
  const routeView = findIndoorRouteView(state.currentRoute, buildingId, floorId);
  await enterIndoorNavigation(buildingId, {
    floorId,
    routeViewId: routeView?.floorView?.view_id || indoorRouteViewId(buildingId, floorId),
    selectedZoneNodeId: "",
    silentStatus: true,
  });
  setStatus(
    `已切换到 ${indoorBuildingRecord(buildingId)?.building_name || getNodeName(buildingId)} ${floorLabelForId(floorId)}。`,
    "info",
  );
}

async function switchIndoorRouteView(viewId) {
  if (!viewId) {
    return;
  }
  state.indoor.currentRouteViewId = viewId;
  if (viewId === "outdoor") {
    state.indoor.mapMode = "outdoor";
    renderIndoorPanel();
    renderMap();
    setStatus("当前优先查看室外路线，可切换到室内楼层查看楼内段。", "info");
    return;
  }

  const parsed = parseIndoorRouteViewId(viewId);
  if (!parsed) {
    renderIndoorPanel();
    return;
  }

  const payload = await enterIndoorNavigation(parsed.buildingId, {
    floorId: parsed.floorId,
    routeViewId: viewId,
    selectedZoneNodeId: state.currentRoute?.target_node_id || "",
    silentStatus: true,
  });
  if (!payload) {
    return;
  }
  state.indoor.mapMode = "indoor";
  rememberIndoorRouteViewId(viewId);
  renderMap();
  setStatus(
    `已切换到 ${indoorBuildingRecord(parsed.buildingId)?.building_name || getNodeName(parsed.buildingId)} ${floorLabelForId(parsed.floorId)} 室内路线视图。`,
    "info",
  );
}

function selectIndoorZone(nodeId) {
  state.indoor.selectedZoneNodeId = nodeId || "";
  if (state.indoor.selectedZoneNodeId) {
    setSelectValue("#route-target", state.indoor.selectedZoneNodeId);
  }
  renderIndoorPanel();
}

async function planRouteFromIndoorZone(nodeId) {
  if (!nodeId) {
    return;
  }
  setSelectValue("#route-target", nodeId);
  await planRoute(nodeId);
}

async function planSelectedIndoorRoute() {
  if (!state.indoor.selectedZoneNodeId) {
    setStatus("请先在室内平面图或功能区列表中选择一个目标点。", "error");
    return;
  }
  await planRouteFromIndoorZone(state.indoor.selectedZoneNodeId);
}

async function syncIndoorStateFromRoute(route) {
  const primaryView = findPrimaryIndoorRouteView(route);
  if (!primaryView) {
    renderIndoorPanel();
    return;
  }

  const defaultRouteViewId = route?.ui?.default_route_view
    || primaryView.floorView.view_id
    || indoorRouteViewId(primaryView.buildingView.building_id, primaryView.floorView.floor_id);
  await enterIndoorNavigation(primaryView.buildingView.building_id, {
    floorId: primaryView.floorView.floor_id,
    routeViewId: defaultRouteViewId,
    selectedZoneNodeId: route?.target_node_id || "",
    silentStatus: true,
  });
}

function renderFeatureGrid(navigation) {
  const container = document.querySelector("#feature-grid");
  if (!container) {
    return;
  }
  container.innerHTML = navigation
    .map((item) => {
      const statusLabel = item.id === "route"
        ? "答辩主线"
        : item.id === "help"
          ? "演示说明"
          : item.status === "ready"
            ? "可使用"
            : "功能扩展";
      return `
        <button class="feature-card${item.id === state.activeTab ? " active" : ""}" type="button" data-tab="${escapeHtml(item.id)}">
          <span class="feature-status">${escapeHtml(statusLabel)}</span>
          <strong>${escapeHtml(item.label)}</strong>
          <span>${escapeHtml(item.description)}</span>
        </button>
      `;
    })
    .join("");
}

function renderDemoTour(steps = []) {
  const containers = [
    document.querySelector("#home-tour-steps"),
    document.querySelector("#workspace-tour-steps"),
  ].filter(Boolean);
  if (!containers.length) {
    return;
  }

  const markup = (steps || [])
    .map((step, index) => `
      <button class="tour-step" type="button" data-tour-step="${escapeHtml(step.id)}">
        <span>${index + 1}</span>
        <strong>${escapeHtml(step.label)}</strong>
        <small>${escapeHtml(step.description || "")}</small>
      </button>
    `)
    .join("");

  containers.forEach((container) => {
    container.innerHTML = markup || `<div class="empty-state">暂无演示步骤。</div>`;
  });
}

function findTourStep(stepId) {
  return (state.bootstrap?.demo_tour || []).find((step) => step.id === stepId) || null;
}

async function runGuidedTour() {
  const steps = state.bootstrap?.demo_tour || [];
  if (!steps.length) {
    setStatus("当前站点没有配置演示向导。", "error");
    return;
  }

  for (const step of steps) {
    await runTourStep(step.id, { quietStart: true });
  }
  setStatus("演示向导已完成，可继续查看地图、结果和路径详情。", "success");
}

async function runTourStep(stepId, options = {}) {
  const step = findTourStep(stepId);
  if (!step) {
    setStatus("演示步骤不存在。", "error");
    return;
  }

  if (!options.quietStart) {
    setStatus(`正在执行演示步骤：${step.label}。`, "loading");
  }
  markActiveTourStep(step.id);

  const tab = step.tab || "route";
  switchTab(tab, { openPage: true });

  if (step.action === "scenic_search") {
    document.querySelector("#scenic-keyword").value = step.keyword || "";
    setSelectValue("#scenic-category", step.category || "");
    await runQuery("/api/search/scenic", {
      keyword: step.keyword || "",
      category: step.category || "",
      sort_field: document.querySelector("#scenic-sort").value,
      start_node_id: state.currentStartNodeId,
      limit: 6,
      ...buildInterestPayload(),
    });
    return;
  }

  if (step.action === "single_route") {
    const targetNodeId = firstExistingRouteTargetId([
      step.target_node_id,
      "library",
      defaultRouteTargetId(),
    ]);
    setSelectValue("#route-target", targetNodeId);
    setSelectValue("#route-strategy", "shortest_distance");
    setSelectValue("#route-transport", "mixed");
    await planRoute(targetNodeId);
    return;
  }

  if (step.action === "indoor_route") {
    const targetNodeId = firstExistingRouteTargetId([
      step.target_node_id,
      "lib_reading_room_1",
      "library",
      defaultRouteTargetId(),
    ]);
    setSelectValue("#route-target", targetNodeId);
    await planRoute(targetNodeId);
    return;
  }

  if (step.action === "nearby_search") {
    const centerNodeId = firstExistingRouteTargetId([
      step.center_node_id,
      "library",
      defaultRouteTargetId(),
    ]);
    await runNearbySearch(centerNodeId, {
      category: step.category || "restroom",
      radius_m: step.radius_m || 500,
      keyword: step.keyword || "",
    });
    return;
  }

  if (step.action === "diary_fulltext") {
    document.querySelector("#diary-query").value = step.query || "";
    await runQuery("/api/diaries/fulltext", {
      query: step.query || "",
      limit: 6,
    });
    return;
  }

  if (step.action === "aigc_preview") {
    fillAigcFormFromSample(step.sample_id || defaultAigcSampleId());
    setAigcMode("template");
    await runAigcPreview();
    return;
  }

  setStatus(`暂不支持的演示动作：${step.action}`, "error");
}

function markActiveTourStep(stepId) {
  document.querySelectorAll("[data-tour-step]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tourStep === stepId);
  });
}

function renderHelpPanel(help) {
  document.querySelector("#help-stage").textContent = help.stage;
  const fallbackLaunch = help.fallback_launch_command
    ? `；备用：${help.fallback_launch_command}`
    : "";
  document.querySelector("#help-launch").textContent =
    `启动：${help.launch_command}${fallbackLaunch}，浏览器访问：${help.browser_url}`;
  document.querySelector("#help-flow").innerHTML = help.demo_flow
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  document.querySelector("#help-checks").innerHTML = help.checks
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  const mapAcceptance = document.querySelector("#help-map-acceptance");
  if (mapAcceptance) {
    mapAcceptance.innerHTML = (help.map_acceptance || [])
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
  }
  renderHomeFlow(help.demo_flow || []);
}

function renderHomeFlow(flowItems) {
  const flow = document.querySelector("#home-flow");
  if (!flow) {
    return;
  }
  flow.innerHTML = (flowItems || [])
    .slice(0, 4)
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function updateActiveFeatureCaption() {
  const caption = document.querySelector("#active-feature-caption");
  const startName = getNodeName(state.currentStartNodeId);
  const user = findBootstrapUser(state.currentUserId);
  const interestText = state.currentInterests.length ? state.currentInterests.join("、") : "未选择兴趣";
  const userText = user ? `当前用户：${user.name}` : "当前用户：自定义";
  if (caption) {
    caption.textContent = startName
      ? `当前起点：${startName}；${userText}；兴趣：${interestText}`
      : `${userText}；兴趣：${interestText}`;
  }
  renderWorkspaceContextSummary();
}

function renderWorkspaceContextSummary() {
  const siteSummary = document.querySelector("#context-site-summary");
  const startSummary = document.querySelector("#context-start-summary");
  const userSummary = document.querySelector("#context-user-summary");
  if (!siteSummary && !startSummary && !userSummary) {
    return;
  }

  const site = state.bootstrap?.site || {};
  const startName = getNodeName(state.currentStartNodeId);
  const user = findBootstrapUser(state.currentUserId);
  const interests = state.currentInterests.length
    ? state.currentInterests.slice(0, 3).join("、")
    : "未选择";

  if (siteSummary) {
    siteSummary.textContent = site.name ? `站点：${site.name}` : "站点加载中";
    siteSummary.title = site.location ? `${site.name} · ${site.location}` : siteSummary.textContent;
  }
  if (startSummary) {
    startSummary.textContent = startName ? `起点：${startName}` : "起点待选择";
    startSummary.title = startSummary.textContent;
  }
  if (userSummary) {
    userSummary.textContent = `偏好：${user ? user.name : "自定义"} · ${interests}`;
    userSummary.title = userSummary.textContent;
  }
}

function updateWorkspaceHeading() {
  if (!state.bootstrap) {
    return;
  }

  const secondaryFeatures = {
    aigc: {
      label: "AIGC 轻量预览",
      description: "选择本地图片样例并输入文字描述，直接浏览 GIF 分镜预览。",
    },
  };
  const feature = state.bootstrap.navigation.find((item) => item.id === state.activeTab)
    || secondaryFeatures[state.activeTab];
  const title = document.querySelector("#workspace-title");
  const description = document.querySelector("#workspace-description");
  const descriptionByTab = {
    scenic: "先做地点检索，再从结果卡片直接进入地图定位与路线规划。",
    place: "围绕附近设施和餐饮推荐做答辩展示，结果优先支持定位和继续规划。",
    route: "地图优先展示当前路线、建筑入口和室内导航状态。",
    diary: "用全文检索和管理操作证明结果面板与路线入口可以互相联动。",
    aigc: "选择本地图片样例并输入文字描述，直接浏览 GIF 分镜预览。",
    help: "这里汇总推荐演示链路、启动方式、帮助说明和冻结版口径。",
  };
  if (title) {
    title.textContent = feature ? `${feature.label}工作区` : "工作区";
  }
  if (description) {
    description.textContent = descriptionByTab[state.activeTab]
      || (feature ? feature.description : "完成查询、推荐、路径和日记演示。");
  }
}

function renderPresetButtons(containerSelector, presets, onClick) {
  const container = document.querySelector(containerSelector);
  if (!container) {
    return;
  }
  container.innerHTML = "";

  (presets || []).forEach((preset) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-chip";
    button.textContent = preset.label;
    button.addEventListener("click", () => onClick(preset));
    container.appendChild(button);
  });
}

function handleScenicPreset(preset) {
  document.querySelector("#scenic-keyword").value = preset.keyword || "";
  document.querySelector("#scenic-category").value = preset.category || "";
  void runQuery("/api/search/scenic", {
    keyword: preset.keyword || "",
    category: preset.category || "",
    sort_field: document.querySelector("#scenic-sort").value,
    start_node_id: state.currentStartNodeId,
    limit: 6,
    ...buildInterestPayload(),
  });
}

function handlePlacePreset(preset) {
  document.querySelector("#place-keyword").value = preset.keyword || "";
  document.querySelector("#place-category").value = preset.category || "";
  void runQuery("/api/search/places", buildPlaceSearchPayload({
    keyword: preset.keyword || "",
    category: preset.category || "",
  }));
}

function getNearbyProfile(centerNodeId) {
  if (!centerNodeId) {
    return null;
  }
  return state.bootstrap?.controls?.nearby_profiles?.[centerNodeId] || null;
}

function applyNearbyProfile(centerNodeId, overrides = {}) {
  if (!centerNodeId) {
    return;
  }

  const profile = getNearbyProfile(centerNodeId);
  if (!profile) {
    return;
  }

  const radiusValue = overrides.radius_m ?? profile.default_radius_m;
  const categoryValue = overrides.category !== undefined
    ? overrides.category
    : (profile.default_category ?? "");

  if (radiusValue !== undefined && radiusValue !== null && radiusValue !== "") {
    setSelectValue("#place-radius", String(radiusValue));
  }
  if (categoryValue !== undefined) {
    setSelectValue("#place-category", categoryValue);
  }
}

function buildPlaceSearchPayload(overrides = {}) {
  const centerNodeId = overrides.center_node_id ?? document.querySelector("#place-center-node").value;
  const radiusM = overrides.radius_m ?? document.querySelector("#place-radius").value;
  const payload = {
    keyword: overrides.keyword ?? document.querySelector("#place-keyword").value.trim(),
    category: overrides.category ?? document.querySelector("#place-category").value,
    sort_field: "distance_m",
    start_node_id: state.currentStartNodeId,
    limit: overrides.limit ?? 6,
  };

  if (centerNodeId) {
    payload.center_node_id = centerNodeId;
    payload.radius_m = Number(radiusM || 500);
  } else {
    payload.sort_field = overrides.sort_field ?? document.querySelector("#place-sort").value;
  }

  return payload;
}

async function runNearbySearch(centerNodeId, options = {}) {
  if (!centerNodeId) {
    setStatus("缺少附近查询中心点。", "error");
    return;
  }

  const profile = getNearbyProfile(centerNodeId);
  const currentRadiusValue = document.querySelector("#place-radius").value || 500;
  const currentCategoryValue = document.querySelector("#place-category").value || "";
  const nextRadiusValue = options.radius_m ?? profile?.default_radius_m ?? currentRadiusValue;
  const nextCategoryValue = options.category !== undefined
    ? options.category
    : (profile ? (profile.default_category ?? "") : currentCategoryValue);

  state.nearbyCenterNodeId = centerNodeId;
  switchTab("place");
  setSelectValue("#place-center-node", centerNodeId);
  setSelectValue("#place-radius", String(nextRadiusValue));
  document.querySelector("#place-keyword").value = options.keyword || "";
  document.querySelector("#place-sort").value = "distance_m";
  setSelectValue("#place-category", nextCategoryValue);

  await runQuery("/api/search/places", buildPlaceSearchPayload({
    center_node_id: centerNodeId,
    radius_m: nextRadiusValue,
    keyword: options.keyword || "",
    category: nextCategoryValue,
    sort_field: "distance_m",
  }));
}

function handleCateringPreset(preset) {
  document.querySelector("#catering-keyword").value = preset.keyword || "";
  document.querySelector("#catering-cuisine").value = preset.cuisine || "";
  void runQuery("/api/recommend/catering", {
    keyword: preset.keyword || "",
    cuisine: preset.cuisine || "",
    sort_field: document.querySelector("#catering-sort").value,
    start_node_id: state.currentStartNodeId,
    limit: 6,
  });
}

function handleDiaryPreset(preset) {
  document.querySelector("#diary-query").value = preset.query || "";
  void runQuery("/api/diaries/fulltext", {
    query: preset.query || "",
    limit: 6,
  });
}

function handleAigcPreset(preset) {
  fillAigcFormFromSample(preset.sample_id || defaultAigcSampleId());
  void runAigcPreview();
}

function setAigcMode(mode) {
  state.aigcMode = mode === "live_image" && isAigcLiveAvailable() ? "live_image" : "template";
  document.querySelectorAll("[data-aigc-mode]").forEach((button) => {
    const isActive = button.dataset.aigcMode === state.aigcMode;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
  syncAigcModeAvailability();
}

function currentAigcMode() {
  return state.aigcMode === "live_image" && isAigcLiveAvailable() ? "live_image" : "template";
}

function isAigcLiveAvailable() {
  return Boolean(state.aigcCapabilities?.live_image);
}

function syncAigcModeAvailability() {
  const liveAvailable = isAigcLiveAvailable();
  const reason = state.aigcCapabilities?.live_image_reason || "当前环境未开启实时生成";
  const model = state.aigcCapabilities?.live_image_model || "OpenAI image model";
  document.querySelectorAll("[data-aigc-mode='live_image']").forEach((button) => {
    button.disabled = !liveAvailable;
    button.title = liveAvailable ? `实时生成可用：${model}` : reason;
  });
  const hint = document.querySelector("#aigc-mode-hint");
  if (hint) {
    hint.textContent = liveAvailable
      ? `实时生成已可用，当前模型：${model}；模板预览仍可离线演示。`
      : `${reason}，已默认使用模板预览。`;
  }
}

async function runAigcPreview() {
  const mode = currentAigcMode();
  const isLiveMode = mode === "live_image";
  setStatus(isLiveMode ? "正在调用模型生成 AIGC 实时分镜..." : "正在生成 AIGC 模板预览...", "loading");
  renderAigcLivePreview(null, "loading", isLiveMode ? "正在调用模型生成实时分镜..." : "正在生成模板预览...");
  renderRoute(null, "AIGC 预览生成中。");

  try {
    const response = await apiPost("/api/aigc/preview", {
      sample_id: document.querySelector("#aigc-sample").value,
      prompt: document.querySelector("#aigc-prompt").value.trim(),
      style: document.querySelector("#aigc-style").value,
      duration_s: document.querySelector("#aigc-duration").value,
      mode,
      provider: "openai",
      frame_count: document.querySelector("#aigc-frame-count").value,
    });

    state.currentResults = response.results || response.data || [];
    state.currentRoute = null;
    state.focusedNodeId = "";
    renderResults(response);
    renderRoute(null, "AIGC 预览不产生路径；如需导航，请从查询或日记结果进入路线规划。");
    renderMap();

    if (!response.success) {
      renderAigcLivePreview(null, "error", response.message || "AIGC 预览生成失败");
      setStatus(response.message || "AIGC 预览生成失败", "error");
      return;
    }

    const preview = state.currentResults[0];
    renderAigcLivePreview(preview, "ready");
    const statusSource = preview.generation_mode === "live_image"
      ? "实时生成成功"
      : preview.generation_mode === "template_fallback"
        ? `已回退到模板预览：${preview.fallback_reason || "实时生成不可用"}`
        : "模板预览已生成";
    setStatus(
      `AIGC ${statusSource}：${preview.title}。`,
      "success",
    );
  } catch (error) {
    state.currentResults = [];
    state.currentRoute = null;
    state.focusedNodeId = "";
    renderResults({
      success: false,
      message: `AIGC 预览失败：${error.message}`,
      total: 0,
      query_type: "aigc_preview_error",
      results: [],
    });
    renderAigcLivePreview(null, "error", `AIGC 预览失败：${error.message}`);
    renderRoute(null, "AIGC 预览失败。");
    renderMap();
    setStatus(`AIGC 预览失败：${error.message}`, "error");
  }
}

function fillAigcFormFromSample(sampleId) {
  const sample = findAigcSample(sampleId) || findAigcSample(defaultAigcSampleId());
  if (!sample) {
    return;
  }

  setSelectValue("#aigc-sample", sample.sample_id);
  document.querySelector("#aigc-image").value = sample.image_placeholder || "";
  document.querySelector("#aigc-prompt").value = sample.text_prompt || "";
  setSelectValue("#aigc-style", sample.style || "");
  document.querySelector("#aigc-duration").value = sample.duration_s || 8;
  renderAigcLivePreview(sample, "sample");
}

function findAigcSample(sampleId) {
  if (!state.bootstrap || !Array.isArray(state.bootstrap.aigc_samples)) {
    return null;
  }
  return state.bootstrap.aigc_samples.find((item) => item.sample_id === sampleId) || null;
}

function defaultAigcSampleId() {
  if (!state.bootstrap || !Array.isArray(state.bootstrap.aigc_samples)) {
    return "";
  }
  return state.bootstrap.aigc_samples[0]?.sample_id || "";
}

async function createDiaryFromForm() {
  const payload = collectDiaryFormPayload();
  await runDiaryManagement(
    "/api/diaries/create",
    payload,
    "日记创建成功，已在结果区展示并可直接规划路线。",
    { keepSelected: true },
  );
}

async function updateDiaryFromForm() {
  const diaryId = selectedDiaryId();
  if (!diaryId) {
    setStatus("请先从日记结果卡片载入一条日记，或先创建一条日记。", "error");
    return;
  }

  await runDiaryManagement(
    "/api/diaries/update",
    {
      id: diaryId,
      updates: collectDiaryFormPayload(),
    },
    "日记更新成功，最新内容已在结果区展示。",
    { keepSelected: true },
  );
}

async function rateDiaryFromForm() {
  const diaryId = selectedDiaryId();
  const rating = document.querySelector("#diary-rating").value;
  if (!diaryId) {
    setStatus("请先选择要评分的日记。", "error");
    return;
  }
  if (rating === "") {
    setStatus("请先填写 0 到 5 之间的评分。", "error");
    return;
  }

  await rateDiary(diaryId, rating);
}

async function rateDiary(diaryId, rating) {
  await runDiaryManagement(
    "/api/diaries/rate",
    {
      id: diaryId,
      rating,
    },
    "日记评分已更新。",
    { keepSelected: true },
  );
}

async function deleteDiary(diaryId) {
  await runDiaryManagement(
    "/api/diaries/delete",
    { id: diaryId },
    "日记已从当前内存态演示数据中删除。",
    { clearSelected: true },
  );
}

async function runDiaryManagement(url, payload, successMessage, options = {}) {
  setStatus("正在提交日记管理操作...", "loading");
  renderRoute(null, "日记管理操作中。");

  try {
    const response = await apiPost(url, payload);
    state.currentResults = response.results || response.data || [];
    state.currentRoute = null;
    state.focusedNodeId = firstMappableNodeId(state.currentResults);
    renderResults(response);
    renderRoute(null);
    renderMap();
    syncDiaryStats(response);

    if (!response.success) {
      setStatus(response.message || "日记管理操作失败", "error");
      return;
    }

    const firstResult = state.currentResults[0];
    if (options.clearSelected) {
      clearDiaryManagementForm();
    } else if (options.keepSelected && firstResult) {
      fillDiaryManagementForm(firstResult);
    }

    setStatus(successMessage, "success");
  } catch (error) {
    state.currentResults = [];
    state.currentRoute = null;
    state.focusedNodeId = "";
    renderResults({
      success: false,
      message: `日记管理操作失败：${error.message}`,
      total: 0,
      query_type: "diary_management_error",
      results: [],
    });
    renderRoute(null, "日记管理操作失败。");
    renderMap();
    setStatus(`日记管理操作失败：${error.message}`, "error");
  }
}

function collectDiaryFormPayload() {
  const ratingValue = document.querySelector("#diary-rating").value;
  const payload = {
    title: document.querySelector("#diary-title").value.trim(),
    content: document.querySelector("#diary-content").value.trim(),
    destination: document.querySelector("#diary-destination").value.trim(),
    destination_node_id: document.querySelector("#diary-destination-node").value,
    tags: splitListInput(document.querySelector("#diary-tags").value),
    images: splitListInput(document.querySelector("#diary-images").value),
    videos: splitListInput(document.querySelector("#diary-videos").value),
  };

  if (ratingValue !== "") {
    payload.rating = Number(ratingValue);
  }
  return payload;
}

function splitListInput(value) {
  return String(value || "")
    .replaceAll("，", ",")
    .replaceAll("、", ",")
    .replaceAll(";", ",")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function selectedDiaryId() {
  return state.selectedDiaryId || document.querySelector("#diary-edit-id").value.trim();
}

function loadDiaryIntoForm(diaryId) {
  const diary = state.currentResults.find((item) => item.id === diaryId || item.diary_id === diaryId);
  if (!diary) {
    setStatus("当前结果中找不到这条日记，无法载入编辑。", "error");
    return;
  }

  fillDiaryManagementForm(diary);
  switchTab("diary");
  setStatus(`已载入日记：${diary.title || diary.id}。`, "info");
}

function fillDiaryManagementForm(diary) {
  const diaryId = diary.id || diary.diary_id || "";
  state.selectedDiaryId = diaryId;
  document.querySelector("#diary-edit-id").value = diaryId;
  document.querySelector("#diary-selected-label").textContent = diaryId
    ? `当前编辑：${diaryId}`
    : "当前为新建模式";
  document.querySelector("#diary-title").value = diary.title || "";
  document.querySelector("#diary-content").value = diary.content || diary.snippet || "";
  document.querySelector("#diary-destination").value = diary.destination || "";
  setSelectValue("#diary-destination-node", diary.destination_node_id || diary.route_target_node_id || "");
  document.querySelector("#diary-rating").value = diary.rating !== undefined ? diary.rating : "";
  document.querySelector("#diary-tags").value = Array.isArray(diary.tags) ? diary.tags.join(", ") : "";
  document.querySelector("#diary-images").value = Array.isArray(diary.images) ? diary.images.join(", ") : "";
  document.querySelector("#diary-videos").value = Array.isArray(diary.videos) ? diary.videos.join(", ") : "";
}

function clearDiaryManagementForm() {
  state.selectedDiaryId = "";
  const fields = [
    "#diary-edit-id",
    "#diary-title",
    "#diary-content",
    "#diary-destination",
    "#diary-rating",
    "#diary-tags",
    "#diary-images",
    "#diary-videos",
  ];
  fields.forEach((selector) => {
    const element = document.querySelector(selector);
    if (element) {
      element.value = "";
    }
  });
  setSelectValue("#diary-destination-node", "");
  const selectedLabel = document.querySelector("#diary-selected-label");
  if (selectedLabel) {
    selectedLabel.textContent = "当前为新建模式";
  }
}

function syncDiaryStats(response) {
  const recordCount = response.ui ? response.ui.record_count : undefined;
  const statDiaries = document.querySelector("#stat-diaries");
  if (recordCount !== undefined && statDiaries) {
    statDiaries.textContent = String(recordCount);
  }
}

function handleRoutePreset(preset) {
  const targetNodeId = preset.target_node_id || "";
  if (!routeTargetRecord(targetNodeId)) {
    setStatus("当前站点不支持该路线快捷入口。", "error");
    return;
  }
  setSelectValue("#route-target", targetNodeId);
  void planRoute(targetNodeId);
}

function handleMultiRoutePreset(preset) {
  const targetNodeIds = preset.target_node_ids || [];
  if (!targetNodeIds.length || targetNodeIds.some((targetNodeId) => !routeTargetRecord(targetNodeId))) {
    setStatus("当前站点不支持该多目标路线快捷入口。", "error");
    return;
  }
  setMultipleSelectValues("#multi-route-targets", targetNodeIds);
  void planMultiRoute(targetNodeIds);
}

function switchMapRenderer(renderer) {
  if (!state.bootstrap) {
    return;
  }

  const renderers = availableMapRenderers();
  if (!renderers.includes(renderer)) {
    setStatus(`当前站点不支持地图渲染器：${renderer}。`, "error");
    return;
  }

  state.mapRenderer = renderer;
  setMapRendererVisibility(renderer);
  renderMap();
  const label = renderer === "leaflet_geo" ? "Leaflet 真实地图" : "SVG 稳定简图";
  setStatus(`地图已切换到 ${label}。`, "info");
}

function switchBasemapMode(mode) {
  if (!state.bootstrap) {
    return;
  }

  const basemapMode = resolveBasemapMode(mode);
  if (!basemapMode) {
    setStatus(`当前站点不支持底图模式：${mode}。`, "error");
    return;
  }

  state.basemapMode = basemapMode;
  state.basemapSourceIndex = 0;
  state.basemapError = "";
  syncLeafletBasemapLayer();
  renderMap();
  setStatus(`底图已切换到 ${basemapModeLabel(basemapMode)}。`, "info");
}

function toggleOsmLayer(layerId) {
  if (!state.bootstrap || !layerId) {
    return;
  }

  if (!availableOsmLayerConfigs().some((item) => item.id === layerId)) {
    setStatus(`当前站点不支持本地 OSM 图层：${layerId}。`, "error");
    return;
  }

  state.osmLayerVisibility[layerId] = !state.osmLayerVisibility[layerId];
  if (state.leaflet.map) {
    syncLeafletOsmLayers(state.osmLayers);
    syncLeafletBaseLayers(state.mapGeoJson);
    syncLeafletRouteLayer();
    syncLeafletLayerOrder();
  }
  syncMapDemoPanel();
  setStatus(`本地 OSM 图层已${state.osmLayerVisibility[layerId] ? "开启" : "关闭"}：${osmLayerLabel(layerId)}。`, "info");
}

function toggleWhiteRoadRole(role) {
  if (!Object.prototype.hasOwnProperty.call(state.whiteRoadRoleVisibility, role)) {
    return;
  }

  const visibleCount = Object.values(state.whiteRoadRoleVisibility).filter(Boolean).length;
  if (state.whiteRoadRoleVisibility[role] && visibleCount <= 1) {
    setStatus("至少保留一个白线节点角色用于检查。", "info");
    return;
  }

  state.whiteRoadRoleVisibility[role] = !state.whiteRoadRoleVisibility[role];
  refreshLeafletInspectionLayers();
  setStatus(
    `${whiteRoadRoleLabel(role)} 已${state.whiteRoadRoleVisibility[role] ? "显示" : "隐藏"}。`,
    "info",
  );
}

function togglePathNodeVisibility(isVisible) {
  state.pathNodesVisible = Boolean(isVisible);
  if (!state.pathNodesVisible && isPathNodeId(state.focusedNodeId)) {
    state.focusedNodeId = "";
  }
  if (selectedMapRenderer() === "leaflet_geo") {
    refreshLeafletInspectionLayers();
  } else {
    renderMap();
  }
  setStatus(
    state.pathNodesVisible
      ? "路径节点已显示，可继续按角色筛选。"
      : "路径节点已隐藏，仅保留地点节点。",
    "info",
  );
}

function refreshLeafletInspectionLayers() {
  if (!state.leaflet.map || selectedMapRenderer() !== "leaflet_geo" || !state.mapGeoJson) {
    syncMapDemoPanel();
    return;
  }

  state.leaflet.baseGeoJson = null;
  syncLeafletBaseLayers(state.mapGeoJson);
  syncLeafletRouteLayer();
  syncLeafletLayerOrder();
  syncLeafletCaption();
  syncMapDemoPanel();
}

async function runMapDemoAction(action) {
  if (!state.bootstrap) {
    setStatus("地图数据尚未加载，无法执行演示动作。", "error");
    return;
  }

  if (action === "single-route") {
    const scenario = resolveDemoRouteScenario("single");
    if (!scenario) {
      setStatus("当前站点没有可用的单目标演示路线。", "error");
      return;
    }
    applyDemoStartNode(scenario.start_node_id);
    setSelectValue("#route-target", scenario.target_node_id);
    setSelectValue("#route-strategy", "shortest_time");
    setSelectValue("#route-transport", "mixed");
    switchTab("route");
    await planRoute(scenario.target_node_id);
    return;
  }

  if (action === "multi-route") {
    const scenario = resolveDemoRouteScenario("multi");
    if (!scenario) {
      setStatus("当前站点没有可用的多目标演示路线。", "error");
      return;
    }
    applyDemoStartNode(scenario.start_node_id);
    setSelectValue("#route-strategy", "shortest_time");
    setSelectValue("#route-transport", "mixed");
    setMultipleSelectValues("#multi-route-targets", scenario.target_node_ids);
    const returnToStart = document.querySelector("#multi-route-return");
    if (returnToStart) {
      returnToStart.checked = scenario.return_to_start;
    }
    switchTab("route");
    await planMultiRoute(scenario.target_node_ids);
    return;
  }

  if (action === "clear-route") {
    state.focusedNodeId = "";
    clearRoute("演示路线已清空。");
    setStatus("演示路线已清空，地图保留当前渲染器。", "info");
  }
}

function resolveDemoRouteScenario(kind) {
  const configured = DEMO_ROUTE_SCENARIOS[kind];
  if (!configured) {
    return null;
  }

  const startNodeId = resolveDemoStartNodeId(configured.start_node_id);
  if (!startNodeId) {
    return null;
  }

  if (kind === "single") {
    const targetNodeId = firstExistingRouteTargetId([
      configured.target_node_id,
      "library",
      "second_gate",
      "canteen",
    ]);
    return targetNodeId
      ? { ...configured, start_node_id: startNodeId, target_node_id: targetNodeId }
      : null;
  }

  const configuredTargetIds = (configured.target_node_ids || []).filter((targetNodeId) => routeTargetRecord(targetNodeId));
  const targetNodeIds = configuredTargetIds.length
    ? configuredTargetIds
    : (state.bootstrap?.route_targets || []).slice(0, 2).map((item) => item.id).filter(Boolean);
  return targetNodeIds.length
    ? { ...configured, start_node_id: startNodeId, target_node_ids: targetNodeIds }
    : null;
}

function resolveDemoStartNodeId(preferredStartNodeId) {
  const startIds = startNodeIdSet();
  if (startIds.has(preferredStartNodeId)) {
    return preferredStartNodeId;
  }
  const defaultStartNodeId = state.bootstrap?.default_start_node || "";
  if (startIds.has(defaultStartNodeId)) {
    return defaultStartNodeId;
  }
  return (state.bootstrap?.start_nodes || [])[0]?.id || "";
}

function firstExistingRouteTargetId(candidates = []) {
  for (const targetNodeId of candidates) {
    if (targetNodeId && routeTargetRecord(targetNodeId)) {
      return targetNodeId;
    }
  }
  return defaultRouteTargetId();
}

function applyDemoStartNode(nodeId) {
  const startSelect = document.querySelector("#global-start-node");
  if (!startSelect) {
    return;
  }
  const hasNode = Array.from(startSelect.options).some((option) => option.value === nodeId);
  if (!hasNode) {
    return;
  }
  state.currentStartNodeId = nodeId;
  setSelectValue("#global-start-node", nodeId);
  updateActiveFeatureCaption();
}

async function runQuery(url, payload) {
  setStatus(feedback("query_loading", "正在查询，请稍候..."), "loading");
  renderResults({
    success: true,
    message: "正在查询...",
    total: 0,
    query_type: "loading",
    results: [],
  });
  revealResultPanel();
  renderRoute(null, "查询执行中，路线会在规划后显示。");

  try {
    const response = await apiPost(url, payload);
    rememberSearch(searchLabelFromPayload(payload), response.query_type, payload, url);
    state.currentResults = response.results || response.data || [];
    state.currentRoute = null;
    state.focusedNodeId = firstMappableNodeId(state.currentResults);
    renderResults(response);
    revealResultPanel();
    renderRoute(null);
    renderMap();

    if (!response.success) {
      setStatus(response.message || "查询失败", "error");
      return;
    }

    if (state.currentResults.length === 0) {
      setStatus(feedback("query_empty", "查询成功，但当前没有命中结果。"), "empty");
      return;
    }

    const routeableCount = response.ui ? response.ui.routeable_result_count : 0;
    setStatus(
      `查询成功，共返回 ${response.total} 条结果，其中 ${routeableCount} 条可直接规划路线。`,
      "success",
    );
  } catch (error) {
    state.currentResults = [];
    state.currentRoute = null;
    state.focusedNodeId = "";
    renderResults({
      success: false,
      message: `查询失败：${error.message}`,
      total: 0,
      query_type: "query_error",
      results: [],
    });
    revealResultPanel();
    renderRoute(null, "查询失败，请调整条件后重试。");
    renderMap();
    setStatus(`查询失败：${error.message}`, "error");
  }
}

async function planRoute(targetNodeId) {
  if (!targetNodeId) {
    state.currentRoute = null;
    renderRoute(null, "当前结果缺少可规划的目标点。");
    renderMap();
    setStatus("当前结果缺少可规划的目标点。", "error");
    return;
  }

  setStatus(feedback("route_loading", "正在规划路径，请稍候..."), "loading");
  renderRoute(null, "正在规划路径...");

  try {
    const response = await apiPost("/api/route", {
      start_node_id: state.currentStartNodeId,
      target_node_id: targetNodeId,
      strategy: document.querySelector("#route-strategy").value,
      transport_mode: document.querySelector("#route-transport").value,
    });

    if (!response.success) {
      state.currentRoute = null;
      renderRoute(null, response.message || feedback("route_unreachable", "当前路径不可达。"));
      renderMap();
      setStatus(response.message || "路径规划失败", "error");
      return;
    }

    state.currentRoute = response;
    state.focusedNodeId = response.target_node_id;
    await syncIndoorStateFromRoute(response);
    renderRoute(response);
    renderMap();
    setStatus(
      `路径规划成功：${response.start_node_name} -> ${response.target_node_name}。`,
      "success",
    );
  } catch (error) {
    state.currentRoute = null;
    renderRoute(null, `路径规划失败：${error.message}`);
    renderMap();
    setStatus(`路径规划失败：${error.message}`, "error");
  }
}

async function planMultiRoute(targetNodeIds) {
  if (!targetNodeIds.length) {
    state.currentRoute = null;
    renderRoute(null, "请至少选择 1 个目标点。");
    renderMap();
    setStatus("多目标路径至少需要选择 1 个目标点。", "error");
    return;
  }

  setStatus("正在规划多目标路径，请稍候...", "loading");
  renderRoute(null, "正在规划多目标路径...");

  try {
    const response = await apiPost("/api/route/multi", {
      start_node_id: state.currentStartNodeId,
      target_node_ids: targetNodeIds,
      strategy: document.querySelector("#route-strategy").value,
      transport_mode: document.querySelector("#route-transport").value,
      return_to_start: document.querySelector("#multi-route-return").checked,
    });

    if (!response.success) {
      state.currentRoute = null;
      renderRoute(null, response.message || "多目标路径规划失败。");
      renderMap();
      setStatus(response.message || "多目标路径规划失败", "error");
      return;
    }

    state.currentRoute = response;
    state.focusedNodeId = "";
    await syncIndoorStateFromRoute(response);
    renderRoute(response);
    renderMap();
    setStatus(
      `多目标路径规划成功：${response.summary.visit_order_text}。`,
      "success",
    );
  } catch (error) {
    state.currentRoute = null;
    renderRoute(null, `多目标路径规划失败：${error.message}`);
    renderMap();
    setStatus(`多目标路径规划失败：${error.message}`, "error");
  }
}

function clearRoute(message = "暂无路径") {
  state.currentRoute = null;
  renderRoute(null, message);
  renderMap();
}

function renderResults(response) {
  const container = document.querySelector("#results-list");
  const meta = document.querySelector("#result-meta");
  const items = response.results || response.data || [];
  const queryType = response.query_type || "query";
  state.currentQueryType = queryType;

  if (!items.length) {
    state.selectedResultIndex = -1;
    container.className = "card-list empty-state";
    container.innerHTML = renderEmptyResultState(response);
    meta.textContent = "0 条结果";
    closeResultDetailDrawer();
    return;
  }

  container.className = "card-list";
  meta.textContent = resultMetaText(response.total, queryType, response.ui);
  container.innerHTML = items
    .map((item, index) => renderResultCard(item, index, queryType))
    .join("");
  if (state.selectedResultIndex < 0 || state.selectedResultIndex >= items.length) {
    state.selectedResultIndex = firstSelectableResultIndex(items);
  }
  syncResultSelection();
  if (isResultDetailOpen()) {
    renderResultDetailDrawer(state.selectedResultIndex);
  }
}

function firstSelectableResultIndex(items = state.currentResults) {
  if (!items.length) {
    return -1;
  }
  const mappableIndex = items.findIndex((item) => resolveResultRouteTargetId(item));
  return mappableIndex >= 0 ? mappableIndex : 0;
}

function selectResultByIndex(index, options = {}) {
  if (!Number.isInteger(index) || index < 0 || index >= state.currentResults.length) {
    return false;
  }
  state.selectedResultIndex = index;
  if (options.focusMap) {
    focusResultMapNode(index);
  }
  syncResultSelection();
  if (options.openDetail) {
    openResultDetailDrawer(index);
  } else if (isResultDetailOpen()) {
    renderResultDetailDrawer(index);
  }
  if (options.scrollIntoView) {
    document.querySelector(`[data-result-index="${index}"]`)?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }
  return true;
}

function selectResultByNodeId(nodeId, options = {}) {
  if (!nodeId) {
    return false;
  }
  const index = state.currentResults.findIndex((item) => resolveResultRouteTargetId(item) === nodeId);
  if (index < 0) {
    return false;
  }
  return selectResultByIndex(index, {
    focusMap: options.focusMap !== false,
    openDetail: options.openDetail !== false,
    scrollIntoView: options.scrollIntoView !== false,
  });
}

function focusResultMapNode(index) {
  const item = state.currentResults[index];
  const nodeId = item ? resolveResultRouteTargetId(item) : "";
  if (!nodeId || state.focusedNodeId === nodeId) {
    return;
  }
  state.focusedNodeId = nodeId;
  renderMap();
}

function syncResultSelection() {
  document.querySelectorAll("[data-result-index]").forEach((card) => {
    const isSelected = Number(card.dataset.resultIndex) === state.selectedResultIndex;
    card.classList.toggle("is-selected", isSelected);
    card.setAttribute("aria-selected", isSelected ? "true" : "false");
  });
}

function isResultDetailOpen() {
  const drawer = document.querySelector("#result-detail-drawer");
  return Boolean(drawer && !drawer.hidden);
}

function openResultDetailDrawer(index = state.selectedResultIndex) {
  const drawer = document.querySelector("#result-detail-drawer");
  if (!drawer) {
    return;
  }
  renderResultDetailDrawer(index);
  drawer.hidden = false;
  drawer.classList.add("is-open");
}

function closeResultDetailDrawer() {
  const drawer = document.querySelector("#result-detail-drawer");
  if (!drawer) {
    return;
  }
  drawer.hidden = true;
  drawer.classList.remove("is-open");
}

function renderResultDetailDrawer(index = state.selectedResultIndex) {
  const content = document.querySelector("#result-detail-content");
  if (!content) {
    return;
  }
  const item = state.currentResults[index];
  if (!item) {
    content.innerHTML = `<p class="empty-detail-text">选择一个结果查看详情。</p>`;
    return;
  }

  const matchDetails = matchDetailsForItem(item);
  const rawTitle = item.name || item.title || item.route_target_name || "未命名结果";
  const rawDescription = item.snippet || item.content || item.text_prompt || item.description || "暂无更多说明。";
  const routeTarget = resolveResultRouteTargetId(item);
  const focusNode = item.has_map_location ? routeTarget : "";
  const indoorContext = routeTarget ? resolveIndoorContextForTarget(routeTarget) : null;
  const metrics = renderResultDetailMetrics(item, routeTarget);
  const mediaMarkup = renderMediaPlaceholders(item);
  const aigcMarkup = isAigcResult(item, state.currentQueryType) ? renderAigcPreview(item) : "";

  const actions = [
    focusNode ? `<button class="ghost-button" type="button" data-focus-node="${escapeHtml(focusNode)}">定位</button>` : "",
    routeTarget ? `<button class="route-button" type="button" data-route-target="${escapeHtml(routeTarget)}">规划路线</button>` : "",
    routeTarget ? `<button class="ghost-button" type="button" data-nearby-center="${escapeHtml(routeTarget)}">查附近设施</button>` : "",
    indoorContext ? `<button class="ghost-button" type="button" data-enter-indoor="${escapeHtml(indoorContext.buildingId)}" data-indoor-floor="${escapeHtml(indoorContext.floorId || "")}" data-indoor-zone-target="${escapeHtml(indoorContext.targetNodeId)}">进入室内导航</button>` : "",
  ].filter(Boolean).join("");

  content.innerHTML = `
    <div class="detail-kicker">${escapeHtml(item.category_label || resultTypeLabel(state.currentQueryType))}</div>
    <h3>${highlightMatchedText(rawTitle, matchDetails, ["name", "title"])}</h3>
    ${metrics ? `<div class="card-metrics detail-metrics">${metrics}</div>` : ""}
    <p>${highlightMatchedText(rawDescription, matchDetails, ["description", "content"])}</p>
    ${renderHighlightedFacets(item, matchDetails)}
    ${renderMatchDetails(item)}
    ${actions ? `<div class="detail-action-row">${actions}</div>` : ""}
    ${mediaMarkup}
    ${aigcMarkup}
  `;
}

function renderResultDetailMetrics(item, routeTarget) {
  const distanceText = formatDistance(item.distance_m, item.distance_status);
  return [
    routeTarget ? `<span class="metric-pill metric-pill-strong">目的地 ${escapeHtml(getNodeName(routeTarget))}</span>` : "",
    distanceText ? `<span class="metric-pill metric-pill-strong">${escapeHtml(distanceText)}</span>` : "",
    item.rating !== undefined ? `<span class="metric-pill">评分 ${Number(item.rating).toFixed(1)}</span>` : "",
    item.heat !== undefined ? `<span class="metric-pill">热度 ${item.heat}</span>` : "",
    item.interest_match_score !== undefined ? `<span class="metric-pill">兴趣 ${Number(item.interest_match_score).toFixed(1)}</span>` : "",
    item.recommendation_score !== undefined ? `<span class="metric-pill">综合 ${Number(item.recommendation_score).toFixed(1)}</span>` : "",
    item.created_at ? `<span class="metric-pill">${escapeHtml(item.created_at)}</span>` : "",
  ].filter(Boolean).join("");
}

function resultTypeLabel(queryType) {
  const labels = {
    scenic_search: "综合查询",
    place_search: "场所查询",
    catering_recommend: "美食推荐",
    diary_fulltext_search: "日记",
    diary_list: "日记",
    aigc_preview: "AIGC",
  };
  return labels[queryType] || "结果详情";
}

function revealResultPanel() {
  if (state.activePage !== "app") {
    return;
  }

  const panel = document.querySelector('[data-expandable-panel="result"]');
  if (!panel) {
    return;
  }

  if (!window.matchMedia("(max-width: 1180px)").matches) {
    return;
  }

  requestAnimationFrame(() => {
    panel.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  });
}

function resultMetaText(total, queryType, ui = {}) {
  const labelMap = {
    scenic_search: "综合查询",
    place_search: "场所查询",
    food_recommend: "美食推荐",
    diary_fulltext_search: "日记检索",
    diary_list: "日记列表",
    diary_create: "日记管理",
    diary_update: "日记管理",
    diary_rate: "日记评分",
    diary_delete: "日记删除",
    aigc_preview: "AIGC 预览",
  };
  const parts = [`${total} 条结果`, labelMap[queryType] || queryType];
  const routeableCount = Number(ui?.routeable_result_count) || 0;
  if (routeableCount > 0) {
    parts.push(`${routeableCount} 条可直接规划路线`);
  }
  return parts.join(" · ");
}

function resolveResultRouteTargetId(item) {
  if (!item || typeof item !== "object") {
    return "";
  }
  return (
    item.route_target_node_id
    || item.destination_node_id
    || item.target_node_id
    || item.node_id
    || item.map_node_id
    || ""
  );
}

function renderMoreActionsMarkup(buttonsMarkup, summaryLabel = "更多操作") {
  if (!buttonsMarkup) {
    return "";
  }

  return `
    <details class="card-secondary-actions result-more-actions">
      <summary>${escapeHtml(summaryLabel)}</summary>
      <div class="card-actions card-actions-secondary">${buttonsMarkup}</div>
    </details>
  `;
}

function renderRouteDetails(geometrySummary) {
  if (!geometrySummary) {
    return "";
  }

  return `
    <details class="route-summary-details">
      <summary>路线细节</summary>
      <div class="route-summary-details-body">
        <p class="technical-note">${escapeHtml(geometrySummary)}</p>
      </div>
    </details>
  `;
}

function renderAigcDetails(pipeline) {
  if (!pipeline.length) {
    return "";
  }

  return `
    <details class="aigc-preview-details">
      <summary>生成链路</summary>
      <div class="aigc-preview-details-body">
        <div class="pipeline-list">
          ${pipeline.map((step) => `<span>${escapeHtml(step)}</span>`).join("")}
        </div>
      </div>
    </details>
  `;
}

function renderAigcLivePreview(item, mode = "empty", message = "") {
  const panel = document.querySelector("#aigc-preview-panel");
  if (!panel) {
    return;
  }

  if (mode === "loading") {
    panel.className = "aigc-live-preview aigc-live-preview-loading";
    panel.textContent = message || "正在生成 AIGC 轻量预览...";
    return;
  }

  if (mode === "error") {
    panel.className = "aigc-live-preview aigc-live-preview-error";
    panel.textContent = message || "AIGC 预览生成失败。";
    return;
  }

  if (!item) {
    panel.className = "aigc-live-preview empty-state";
    panel.textContent = "选择样例并生成预览后，在这里直接展示 JPG / GIF 和分镜。";
    return;
  }

  const isGenerated = mode === "ready" || Array.isArray(item.storyboard_frames);
  const frames = Array.isArray(item.storyboard_frames) ? item.storyboard_frames : [];
  const pipeline = Array.isArray(item.generation_pipeline) ? item.generation_pipeline : [];
  const title = item.title || item.label || item.text_prompt || "AIGC 轻量预览";
  const sourceImage = item.image_placeholder || "";
  const outputPreview = item.preview_placeholder || "";
  const status = item.status || (isGenerated ? "ready" : "sample");
  const summary = item.prompt_summary || item.text_prompt || "";
  const generationMode = item.generation_mode || (isGenerated ? "template_preview" : "sample");
  const sourceLabel = aigcGenerationModeLabel(generationMode);
  const sourceClass = generationMode === "live_image"
    ? "status-pill-primary"
    : generationMode === "template_fallback"
      ? "status-pill-strong"
      : "status-pill-muted";
  const generatedImages = Array.isArray(item.generated_images) ? item.generated_images : [];
  const liveImages = generatedImages.length
    ? generatedImages
    : frames.map((frame) => frame.image_url).filter(Boolean);
  const imageMarkup = sourceImage && /\.(jpe?g|png|webp|gif)$/i.test(sourceImage)
    ? `<img src="${escapeHtml(sourceImage)}" alt="AIGC 输入图片" loading="lazy" />`
    : `<strong>${escapeHtml(sourceImage || "暂无输入图片")}</strong>`;
  const previewMarkup = outputPreview && /\.(gif|jpe?g|png|webp)$/i.test(outputPreview)
    ? `<img src="${escapeHtml(outputPreview)}" alt="AIGC 输出预览" loading="lazy" />`
    : `<strong>${escapeHtml(outputPreview || "生成后显示 GIF 预览")}</strong>`;

  panel.className = `aigc-live-preview${isGenerated ? " aigc-live-preview-ready" : " aigc-live-preview-sample"}`;
  panel.innerHTML = `
    <div class="aigc-live-heading">
      <div>
        <span class="status-pill ${sourceClass}">${escapeHtml(sourceLabel)}</span>
        <h4>${escapeHtml(title)}</h4>
      </div>
      <div class="aigc-preview-meta">
        <span class="metric-pill metric-pill-strong">${escapeHtml(status)}</span>
        ${item.style_label || item.style ? `<span class="metric-pill">${escapeHtml(item.style_label || item.style)}</span>` : ""}
        ${item.duration_s !== undefined ? `<span class="metric-pill">${item.duration_s} 秒</span>` : ""}
        ${item.frame_count !== undefined ? `<span class="metric-pill">${item.frame_count} 张分镜</span>` : ""}
      </div>
    </div>
    ${item.fallback_used ? `<p class="aigc-fallback-note">已回退到模板预览：${escapeHtml(item.fallback_reason || "实时生成不可用")}</p>` : ""}
    ${summary ? `<p class="aigc-preview-summary">${escapeHtml(summary)}</p>` : ""}
    <div class="aigc-live-media-grid">
      <figure class="aigc-live-media-card">
        <figcaption>输入 JPG</figcaption>
        ${imageMarkup}
      </figure>
      <figure class="aigc-live-media-card aigc-live-media-card-primary">
        <figcaption>${generationMode === "live_image" ? "实时分镜播放" : "输出 GIF 预览"}</figcaption>
        ${liveImages.length ? renderAigcGeneratedPlayer(liveImages, frames) : previewMarkup}
      </figure>
    </div>
    ${isGenerated ? renderAigcPreview(item) : ""}
    ${!isGenerated && pipeline.length ? renderAigcDetails(pipeline) : ""}
  `;
}

function aigcGenerationModeLabel(mode) {
  if (mode === "live_image") {
    return "live_image";
  }
  if (mode === "template_fallback") {
    return "template_fallback";
  }
  if (mode === "template_preview") {
    return "template_preview";
  }
  return "当前样例";
}

function renderAigcGeneratedPlayer(images, frames) {
  return `
    <div class="aigc-generated-player" style="--aigc-frame-count:${Math.max(1, images.length)}">
      ${images
        .map((src, index) => {
          const frame = frames[index] || {};
          const title = frame.title || `分镜 ${index + 1}`;
          return `
            <figure class="aigc-generated-frame" style="--aigc-frame-index:${index}">
              <img src="${escapeHtml(src)}" alt="${escapeHtml(title)}" loading="lazy" />
              <figcaption>${escapeHtml(title)}</figcaption>
            </figure>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderResultCard(item, index, queryType = "") {
  const matchDetails = matchDetailsForItem(item);
  const rawTitle = item.name || item.title || item.route_target_name || "未命名结果";
  const rawDescription = item.snippet || item.content || item.text_prompt || item.description || "可从该结果继续规划路线。";
  const title = highlightMatchedText(rawTitle, matchDetails, ["name", "title"]);
  const description = highlightMatchedText(rawDescription, matchDetails, ["description", "content"]);
  const distanceText = formatDistance(item.distance_m, item.distance_status);
  const scoreText = item.score !== undefined ? `相关度 ${item.score}` : "";
  const routeTarget = resolveResultRouteTargetId(item);
  const routeTargetName = routeTarget ? getNodeName(routeTarget) : "";
  const focusNode = item.has_map_location ? routeTarget : "";
  const isSelected = index === state.selectedResultIndex;
  const indoorContext = routeTarget ? resolveIndoorContextForTarget(routeTarget) : null;
  const isDiary = isDiaryResult(item, queryType);
  const isAigc = isAigcResult(item, queryType);
  const diaryId = item.id || item.diary_id || "";
  const mediaMarkup = renderMediaPlaceholders(item);
  const aigcMarkup = isAigc ? renderAigcPreview(item) : "";
  const matchMarkup = renderMatchDetails(item);
  const facetMarkup = renderHighlightedFacets(item, matchDetails);
  const interestMarkup = item.interest_reason
    ? `<p class="interest-reason">${escapeHtml(item.interest_reason)}</p>`
    : "";

  const metrics = [
    routeTargetName ? `<span class="metric-pill metric-pill-strong">目的地 ${escapeHtml(routeTargetName)}</span>` : "",
    item.interest_match_score !== undefined ? `<span class="metric-pill metric-pill-strong">兴趣 ${Number(item.interest_match_score).toFixed(1)}</span>` : "",
    item.recommendation_score !== undefined ? `<span class="metric-pill">综合 ${Number(item.recommendation_score).toFixed(1)}</span>` : "",
    distanceText ? `<span class="metric-pill metric-pill-strong">${escapeHtml(distanceText)}</span>` : "",
    item.nearby_reason ? `<span class="metric-pill">${escapeHtml(item.nearby_reason)}</span>` : "",
    item.category_label ? `<span class="metric-pill">${escapeHtml(item.category_label)}</span>` : "",
    item.rating !== undefined ? `<span class="metric-pill">评分 ${Number(item.rating).toFixed(1)}</span>` : "",
    item.destination ? `<span class="metric-pill">目的地 ${escapeHtml(item.destination)}</span>` : "",
    scoreText ? `<span class="metric-pill">${escapeHtml(scoreText)}</span>` : "",
    item.heat !== undefined ? `<span class="metric-pill">热度 ${item.heat}</span>` : "",
    item.style_label ? `<span class="metric-pill">${escapeHtml(item.style_label)}</span>` : "",
    item.duration_s !== undefined ? `<span class="metric-pill">${item.duration_s} 秒</span>` : "",
    item.status ? `<span class="metric-pill">${escapeHtml(item.status)}</span>` : "",
    item.created_at ? `<span class="metric-pill">${escapeHtml(item.created_at)}</span>` : "",
  ]
    .filter(Boolean)
    .slice(0, PRIORITY_METRIC_LIMIT)
    .join("");

  const primaryButtons = routeTarget
    ? `<button class="route-button" type="button" data-route-target="${escapeHtml(routeTarget)}">规划路线</button>`
    : "";

  const secondaryButtons = [];
  if (focusNode) {
    secondaryButtons.push(`<button class="ghost-button" type="button" data-focus-node="${escapeHtml(focusNode)}">定位</button>`);
  }
  if (routeTarget) {
    secondaryButtons.push(`<button class="ghost-button" type="button" data-nearby-center="${escapeHtml(routeTarget)}">查附近设施</button>`);
  }
  if (indoorContext) {
    secondaryButtons.push(`<button class="ghost-button" type="button" data-enter-indoor="${escapeHtml(indoorContext.buildingId)}" data-indoor-floor="${escapeHtml(indoorContext.floorId || "")}" data-indoor-zone-target="${escapeHtml(indoorContext.targetNodeId)}">进入室内导航</button>`);
  }
  if (isDiary && queryType !== "diary_delete") {
    secondaryButtons.push(`<button class="ghost-button" type="button" data-diary-edit-id="${escapeHtml(diaryId)}">编辑</button>`);
    secondaryButtons.push(`<button class="ghost-button" type="button" data-diary-rate-id="${escapeHtml(diaryId)}">评 5 分</button>`);
    secondaryButtons.push(`<button class="danger-button" type="button" data-diary-delete-id="${escapeHtml(diaryId)}">删除</button>`);
  }

  const secondaryActions = queryType === "diary_delete" && isDiary
    ? `<span class="deleted-badge">已从内存态移除</span>`
    : renderMoreActionsMarkup(secondaryButtons.join(""), isDiary ? "日记管理" : "更多操作");

  return `
    <article
      class="result-card${isSelected ? " is-selected" : ""}"
      data-result-index="${index}"
      data-result-node="${escapeHtml(focusNode || routeTarget || "")}"
      tabindex="0"
      style="animation-delay: ${index * 0.04}s"
    >
      <h4>${title}</h4>
      <div class="card-metrics">${metrics}</div>
      <p>${description}</p>
      ${facetMarkup}
      ${interestMarkup}
      ${matchMarkup}
      ${mediaMarkup}
      ${aigcMarkup}
      ${primaryButtons ? `<div class="card-actions card-actions-primary">${primaryButtons}</div>` : ""}
      ${secondaryActions}
    </article>
  `;
}

function renderEmptyResultState(response) {
  const message = response.message || "暂无结果，请调整关键词或筛选条件。";
  const suggestions = suggestionsForQueryType(response.query_type);
  const suggestionMarkup = suggestions.length
    ? `<div class="empty-suggestion-list">
        ${suggestions.map((item, index) => `
          <button class="quick-chip" type="button" data-empty-suggestion="${escapeHtml(response.query_type || "query")}:${index}">
            ${escapeHtml(item.label)}
          </button>
        `).join("")}
      </div>`
    : "";
  return `
    <div class="empty-result-card">
      <strong>${escapeHtml(message)}</strong>
      ${suggestionMarkup}
    </div>
  `;
}

function suggestionsForQueryType(queryType) {
  const suggestions = state.bootstrap?.empty_result_suggestions || {};
  return suggestions[queryType] || suggestions.scenic_search || [];
}

async function runEmptySuggestion(key) {
  const [queryType, rawIndex] = key.split(":");
  const index = Number(rawIndex);
  const suggestion = (suggestionsForQueryType(queryType) || [])[index];
  if (!suggestion) {
    return;
  }

  switchTab(suggestion.tab || "scenic", { openPage: true });
  applySuggestionToForm(suggestion);
  await runQuery(suggestion.endpoint || "/api/search/scenic", {
    ...(suggestion.payload || {}),
    start_node_id: state.currentStartNodeId,
    limit: 6,
    ...((suggestion.tab || "") === "scenic" ? buildInterestPayload() : {}),
  });
}

function applySuggestionToForm(suggestion) {
  const payload = suggestion.payload || {};
  if (suggestion.tab === "place") {
    document.querySelector("#place-keyword").value = payload.keyword || "";
    setSelectValue("#place-category", payload.category || "");
    return;
  }
  if (suggestion.tab === "diary") {
    document.querySelector("#diary-query").value = payload.query || "";
    return;
  }
  document.querySelector("#scenic-keyword").value = payload.keyword || "";
  setSelectValue("#scenic-category", payload.category || "");
}

function renderMatchDetails(item) {
  const details = matchDetailsForItem(item);
  if (!details.length) {
    return "";
  }

  return `
    <div class="match-detail-list" aria-label="搜索命中解释">
      ${details.slice(0, 3).map((detail) => `
        <span class="match-detail-chip">
          ${escapeHtml(detail.field_label || detail.field || "字段")}
          · ${escapeHtml(matchTypeLabel(detail.match_type))}
          · ${escapeHtml(detail.term || "")}
        </span>
      `).join("")}
    </div>
  `;
}

function matchDetailsForItem(item) {
  return Array.isArray(item._match_detail) ? item._match_detail : [];
}

function renderHighlightedFacets(item, details = matchDetailsForItem(item)) {
  const facets = [
    { field: "tags", label: "标签", values: flattenDisplayValues(item.tags) },
    { field: "keywords", label: "关键词", values: flattenDisplayValues(item.keywords) },
  ];
  const rows = facets
    .map((facet) => {
      const facetDetails = details.filter((detail) => detail.field === facet.field);
      if (!facet.values.length || !facetDetails.length) {
        return "";
      }
      return `
        <div class="highlight-facet-row">
          <span>${escapeHtml(facet.label)}</span>
          <div class="highlight-facet-list">
            ${facet.values.slice(0, 5).map((value) => `
              <span class="highlight-facet-chip">${highlightMatchedText(value, facetDetails, [facet.field])}</span>
            `).join("")}
          </div>
        </div>
      `;
    })
    .filter(Boolean);

  return rows.length ? `<div class="highlight-facet-panel">${rows.join("")}</div>` : "";
}

function highlightMatchedText(value, details = [], fields = []) {
  const text = String(value ?? "");
  if (!text || !details.length) {
    return escapeHtml(text);
  }

  const terms = highlightTermsForDetails(details, fields);
  const ranges = mergeHighlightRanges(collectHighlightRanges(text, terms));
  if (!ranges.length) {
    return escapeHtml(text);
  }

  let cursor = 0;
  let markup = "";
  ranges.forEach((range) => {
    if (range.start > cursor) {
      markup += escapeHtml(text.slice(cursor, range.start));
    }
    markup += `<mark class="search-highlight">${escapeHtml(text.slice(range.start, range.end))}</mark>`;
    cursor = range.end;
  });
  markup += escapeHtml(text.slice(cursor));
  return markup;
}

function highlightTermsForDetails(details, fields = []) {
  const fieldSet = new Set(fields);
  const terms = [];
  details.forEach((detail) => {
    if (fieldSet.size && !fieldSet.has(detail.field)) {
      return;
    }
    [detail.term, detail.matched_text].forEach((candidate) => {
      const normalized = normalizeHighlightTerm(candidate);
      if (normalized.length >= 2 && normalized.length <= 24 && !terms.includes(normalized)) {
        terms.push(normalized);
      }
    });
  });
  return terms.sort((left, right) => right.length - left.length);
}

function collectHighlightRanges(text, terms) {
  if (!terms.length) {
    return [];
  }

  const index = buildNormalizedTextIndex(text);
  const ranges = [];
  terms.forEach((term) => {
    let position = index.normalized.indexOf(term);
    while (position >= 0) {
      const start = index.map[position]?.start;
      const end = index.map[position + term.length - 1]?.end;
      if (start !== undefined && end !== undefined && end > start) {
        ranges.push({ start, end });
      }
      position = index.normalized.indexOf(term, position + 1);
    }
  });
  return ranges;
}

function buildNormalizedTextIndex(text) {
  let normalized = "";
  const map = [];
  let offset = 0;
  for (const char of text) {
    const start = offset;
    const end = start + char.length;
    offset = end;
    if (MATCH_SEPARATOR_PATTERN.test(char)) {
      continue;
    }
    normalized += char.toLocaleLowerCase();
    map.push({ start, end });
  }
  return { normalized, map };
}

function normalizeHighlightTerm(value) {
  return String(value ?? "")
    .trim()
    .toLocaleLowerCase()
    .split("")
    .filter((char) => !MATCH_SEPARATOR_PATTERN.test(char))
    .join("");
}

function mergeHighlightRanges(ranges) {
  if (!ranges.length) {
    return [];
  }
  const ordered = ranges
    .filter((range) => Number.isInteger(range.start) && Number.isInteger(range.end) && range.end > range.start)
    .sort((left, right) => left.start - right.start || right.end - left.end);
  const merged = [];
  ordered.forEach((range) => {
    const previous = merged[merged.length - 1];
    if (!previous || range.start > previous.end) {
      merged.push({ ...range });
      return;
    }
    previous.end = Math.max(previous.end, range.end);
  });
  return merged;
}

function flattenDisplayValues(value) {
  if (value === null || value === undefined || value === "") {
    return [];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => flattenDisplayValues(item));
  }
  if (typeof value === "object") {
    return Object.values(value).flatMap((item) => flattenDisplayValues(item));
  }
  return [String(value)];
}

function matchTypeLabel(matchType) {
  const labels = {
    exact: "精确",
    prefix: "前缀",
    contains: "包含",
    subsequence: "跳字",
    typo: "错字",
  };
  return labels[matchType] || "匹配";
}

function isDiaryResult(item, queryType) {
  return (
    queryType.startsWith("diary") ||
    Boolean(item.diary_id) ||
    item.category_label === "日记"
  );
}

function renderMediaPlaceholders(item) {
  const images = Array.isArray(item.images) ? item.images : [];
  const videos = Array.isArray(item.videos) ? item.videos : [];
  const directMedia = [];
  if (item.image_placeholder) {
    directMedia.push({ kind: "图片占位", value: item.image_placeholder });
  }
  if (item.preview_placeholder) {
    directMedia.push({ kind: "预览占位", value: item.preview_placeholder });
  }
  const mediaItems = directMedia.concat(images
    .map((value) => ({ kind: "图片", value }))
    .concat(videos.map((value) => ({ kind: "视频", value }))));

  if (!mediaItems.length) {
    return "";
  }

  return `
    <div class="media-strip">
      ${mediaItems
        .map((media) => {
          const isImage = /\.(jpe?g|png|gif|webp|bmp)$/i.test(media.value);
          const src = media.value;
          if (isImage) {
            return `<span class="media-chip media-chip-image">
              <span>${escapeHtml(media.kind)}</span>
              <img src="${escapeHtml(src)}" alt="${escapeHtml(media.kind)}" loading="lazy" style="max-width:360px;max-height:200px;border-radius:6px;object-fit:cover;" />
            </span>`;
          }
          return `<span class="media-chip">
            <span>${escapeHtml(media.kind)}</span>
            <strong>${escapeHtml(media.value)}</strong>
          </span>`;
        })
        .join("")}
    </div>
  `;
}

function isAigcResult(item, queryType) {
  return queryType === "aigc_preview" || Boolean(item.storyboard_frames);
}

function renderAigcPreview(item) {
  const frames = Array.isArray(item.storyboard_frames) ? item.storyboard_frames : [];
  const pipeline = Array.isArray(item.generation_pipeline) ? item.generation_pipeline : [];
  const previewSummary = item.prompt_summary || item.text_prompt || "";
  const generationMode = item.generation_mode || "template_preview";
  const generatedImages = Array.isArray(item.generated_images) ? item.generated_images : [];
  const previewMetrics = [
    `<span class="metric-pill metric-pill-strong">${escapeHtml(aigcGenerationModeLabel(generationMode))}</span>`,
    item.style_label ? `<span class="metric-pill">${escapeHtml(item.style_label)}</span>` : "",
    item.duration_s !== undefined ? `<span class="metric-pill">${item.duration_s} 秒</span>` : "",
    item.frame_count !== undefined ? `<span class="metric-pill">${item.frame_count} 张分镜</span>` : "",
  ]
    .filter(Boolean)
    .join("");
  const previewImg = item.preview_placeholder && /\.(gif|jpe?g|png|webp)$/i.test(item.preview_placeholder)
    ? `<div class="aigc-preview-image"><img src="${escapeHtml(item.preview_placeholder)}" alt="AIGC Preview" loading="lazy" style="max-width:480px;max-height:270px;border-radius:8px;object-fit:cover;" /></div>`
    : "";
  return `
    <div class="aigc-preview-block">
      <p class="prototype-notice">${escapeHtml(item.prototype_notice || "")}</p>
      ${previewMetrics ? `<div class="aigc-preview-meta">${previewMetrics}</div>` : ""}
      ${item.fallback_used ? `<p class="aigc-fallback-note">已回退到模板预览：${escapeHtml(item.fallback_reason || "实时生成不可用")}</p>` : ""}
      ${previewSummary ? `<p class="aigc-preview-summary">${escapeHtml(previewSummary)}</p>` : ""}
      ${generatedImages.length ? renderAigcGeneratedPlayer(generatedImages, frames) : previewImg}
      <div class="storyboard-grid">
        ${frames
          .map((frame) => `
            <article class="storyboard-frame">
              <span>${frame.time_s}s</span>
              <strong>${escapeHtml(frame.title)}</strong>
              ${frame.image_url ? `<img src="${escapeHtml(frame.image_url)}" alt="${escapeHtml(frame.title)}" loading="lazy" />` : ""}
              <p>${escapeHtml(frame.visual || frame.caption || "")}</p>
            </article>
          `)
          .join("")}
      </div>
      ${renderAigcDetails(pipeline)}
    </div>
  `;
}

function renderRoute(route, emptyMessage = "暂无路径") {
  const summaryContainer = document.querySelector("#route-summary");
  const stepsContainer = document.querySelector("#route-steps");
  const routeMeta = document.querySelector("#route-meta");

  if (!route) {
    summaryContainer.className = "route-summary empty-state";
    summaryContainer.textContent = emptyMessage;
    stepsContainer.className = "step-list empty-state";
    stepsContainer.textContent = "规划路线后可在这里展开查看步骤。";
    routeMeta.textContent = "尚未规划路径";
    renderIndoorPanel();
    return;
  }

  if (route.route_type === "multi_target") {
    renderMultiRoute(route, summaryContainer, stepsContainer, routeMeta);
    renderIndoorPanel();
    return;
  }

  const summary = route.summary || {};
  const geometrySummary = routeGeometrySummaryText(route);
  const crossLayerText = route.route_overview?.cross_layer
    ? `跨 ${route.route_overview.cross_layer_step_count || 1} 次室内/室外`
    : "室外路线";
  summaryContainer.className = "route-summary";
  summaryContainer.innerHTML = `
    <article class="summary-card">
      <span class="summary-kicker">当前路线</span>
      <h4>${escapeHtml(route.start_node_name)} -> ${escapeHtml(route.target_node_name)}</h4>
      <p>${escapeHtml(routePrimarySentence(route))}</p>
      <div class="summary-grid summary-grid-priority">
        ${renderMetricPill(summary.distance_text, "metric-pill-strong")}
        ${renderMetricPill(summary.time_text, "metric-pill-strong")}
        ${renderMetricPill(crossLayerText)}
        ${renderMetricPill(summary.strategy_text)}
      </div>
      ${renderRouteDetails(geometrySummary)}
    </article>
  `;

  const steps = route.path_steps || [];
  const pathNodeCount = Array.isArray(route.path_node_names) ? route.path_node_names.length : 0;
  routeMeta.textContent = `${steps.length} 步 · ${pathNodeCount} 个路径点`;
  stepsContainer.className = "step-list";
  stepsContainer.innerHTML = renderStepDetails(
    `${steps.length} 个详细步骤`,
    steps.map(renderSingleRouteStep).join(""),
  );
  renderIndoorPanel();
}

function renderMultiRoute(route, summaryContainer, stepsContainer, routeMeta) {
  const summary = route.summary || {};
  const geometrySummary = routeGeometrySummaryText(route);
  summaryContainer.className = "route-summary";
  summaryContainer.innerHTML = `
    <article class="summary-card">
      <span class="summary-kicker">多目标路线</span>
      <h4>${escapeHtml(summary.visit_order_text || "多目标路径")}</h4>
      <p>${escapeHtml(routePrimarySentence(route))}</p>
      <div class="summary-grid summary-grid-priority">
        ${renderMetricPill(summary.distance_text, "metric-pill-strong")}
        ${renderMetricPill(summary.time_text, "metric-pill-strong")}
        ${renderMetricPill(`${summary.target_count || 0} 个目标`)}
        ${renderMetricPill(summary.return_to_start_text || "")}
      </div>
      ${renderRouteDetails(geometrySummary)}
    </article>
  `;

  const legSummaries = route.ui?.leg_summaries || [];
  const displaySteps = route.ui?.display_steps || [];
  routeMeta.textContent = `${legSummaries.length} 段 · ${displaySteps.length} 个关键步骤`;
  stepsContainer.className = "step-list";

  const legMarkup = legSummaries
    .map((leg, index) => `
      <article class="step-card" style="animation-delay: ${index * 0.03}s">
        <h4>第 ${leg.leg_index} 段：${escapeHtml(leg.start_node_name)} -> ${escapeHtml(leg.target_node_name)}</h4>
        <div class="card-metrics">
          <span class="metric-pill">${escapeHtml(leg.distance_text || "")}</span>
          <span class="metric-pill">${escapeHtml(leg.time_text || "")}</span>
          <span class="metric-pill">${leg.step_count} 步</span>
        </div>
        <p>${escapeHtml((leg.path_node_names || []).join(" -> "))}</p>
      </article>
    `)
    .join("");

  const keySteps = displaySteps.slice(0, 12);
  const stepMarkup = keySteps
    .map((step, index) => {
      const edgeName = step.edge_name ? ` · ${escapeHtml(step.edge_name)}` : "";
      return `
        <article class="step-card compact-step" style="animation-delay: ${(index + legSummaries.length) * 0.03}s">
          <h4>第 ${step.leg_index} 段 / 步 ${step.step_index}${edgeName}</h4>
          <p>${escapeHtml(step.from_node_name)} -> ${escapeHtml(step.to_node_name)}</p>
          <div class="card-metrics">
            <span class="metric-pill">${escapeHtml(step.display_layer || step.to_layer || "")}</span>
            <span class="metric-pill">${formatDistance(step.distance_m, "available")}</span>
            <span class="metric-pill">${formatSeconds(step.estimated_time_s)}</span>
          </div>
        </article>
      `;
    })
    .join("");

  const overflowText = displaySteps.length > keySteps.length
    ? `<p class="step-overflow">已展示前 ${keySteps.length} 个关键步骤，完整逐边数据保留在 API 返回中。</p>`
    : "";

  stepsContainer.innerHTML = renderStepDetails(
    `${legSummaries.length} 段路线 · ${displaySteps.length} 个关键步骤`,
    `${legMarkup}${stepMarkup}${overflowText}`,
  );
}

function syncIndoorMapStage() {
  const container = document.querySelector("#indoor-map-view");
  if (!container) {
    syncMapViewToggle();
    return;
  }

  if (state.indoor.loading) {
    const loadingBuilding = indoorBuildingRecord(state.indoor.loading.buildingId);
    container.innerHTML = `
      <div class="indoor-map-empty">
        ${escapeHtml(loadingBuilding?.building_name || state.indoor.loading.buildingId)} ${escapeHtml(floorLabelForId(state.indoor.loading.floorId || ""))} 室内平面图加载中
      </div>
    `;
    setMapRendererVisibility(selectedMapRenderer());
    return;
  }

  if (!hasIndoorMapContext()) {
    container.innerHTML = "";
    state.indoor.mapMode = "outdoor";
    setMapRendererVisibility(selectedMapRenderer());
    return;
  }

  const activeBuilding = indoorBuildingRecord(state.indoor.activeBuildingId);
  const payload = state.indoor.activePayload;
  const activeFloorId = state.indoor.activeFloorId || indoorPayloadFloorId(payload);
  const currentViewId = selectedMapViewMode() === "indoor"
    ? resolveActiveIndoorRouteViewId()
    : (state.indoor.currentRouteViewId || state.currentRoute?.ui?.default_route_view || indoorRouteViewId(activeBuilding.building_id, activeFloorId));
  const routeContext = findIndoorRouteView(state.currentRoute, activeBuilding.building_id, activeFloorId);

  container.innerHTML = `
    <div class="indoor-map-inner">
      ${renderIndoorFloorplan(payload, {
        routeContext,
        currentViewId,
        selectedZoneNodeId: state.indoor.selectedZoneNodeId,
      })}
    </div>
  `;
  setMapRendererVisibility(selectedMapRenderer());
}

function renderIndoorPanel() {
  const panel = document.querySelector("#indoor-panel");
  const meta = document.querySelector("#indoor-panel-meta");
  const body = document.querySelector("#indoor-panel-body");
  if (!meta || !body) {
    return;
  }
  renderIndoorQuickStart();
  syncIndoorMapStage();

  const supportedBuildings = state.indoor.buildings || [];
  if (!supportedBuildings.length) {
    if (panel) {
      panel.open = false;
    }
    meta.textContent = "当前站点未提供室内导航数据";
    body.className = "indoor-panel-body empty-state";
    body.textContent = "当前站点没有可用的室内模板图。";
    return;
  }

  if (state.indoor.loading) {
    if (panel) {
      panel.open = true;
    }
    const loadingBuilding = indoorBuildingRecord(state.indoor.loading.buildingId);
    meta.textContent = `正在加载 ${loadingBuilding?.building_name || state.indoor.loading.buildingId}…`;
    body.className = "indoor-panel-body";
    body.innerHTML = `
      <div class="indoor-state-card is-loading">
        <strong>室内平面图加载中</strong>
        <p>${escapeHtml(loadingBuilding?.building_name || state.indoor.loading.buildingId)} ${escapeHtml(floorLabelForId(state.indoor.loading.floorId || ""))} 正在准备。</p>
      </div>
    `;
    return;
  }

  const activeBuilding = indoorBuildingRecord(state.indoor.activeBuildingId);
  const payload = state.indoor.activePayload;
  if (!activeBuilding || !payload || payload.building_id !== activeBuilding.building_id) {
    if (panel) {
      panel.open = false;
    }
    meta.textContent = state.indoor.error || `支持 ${supportedBuildings.length} 栋建筑室内导航`;
    body.className = "indoor-panel-body";
    body.innerHTML = renderIndoorEmptyState(supportedBuildings, state.indoor.error);
    return;
  }

  const activeFloorId = state.indoor.activeFloorId || indoorPayloadFloorId(payload);
  const activeFloorLabel = indoorPayloadFloorLabel(payload);
  const currentViewId = state.indoor.currentRouteViewId
    || state.currentRoute?.ui?.default_route_view
    || indoorRouteViewId(activeBuilding.building_id, activeFloorId);
  const routeContext = findIndoorRouteView(state.currentRoute, activeBuilding.building_id, activeFloorId);
  const selectedZone = (payload.zones || []).find((item) => item.id === state.indoor.selectedZoneNodeId) || null;
  const currentRouteHasIndoor = Boolean((state.currentRoute?.ui?.indoor_route_views || []).length);
  const routeNotice = currentRouteHasIndoor
    ? currentViewId === "outdoor"
      ? "当前路线默认查看室外段；切换到室内路线按钮可查看楼内路径。"
      : routeContext?.floorView?.route_node_ids?.length
        ? `当前楼层命中 ${routeContext.floorView.route_node_ids.length} 个室内路径点。`
        : "当前路线未经过该楼层，可先浏览平面图或切换到其他楼层。"
    : "先选择楼层和功能区，再点击规划路线。";
  meta.textContent = `${activeBuilding.building_name} · ${activeFloorLabel} · ${(payload.zones || []).length} 个功能区`;
  if (panel) {
    panel.open = true;
  }
  body.className = "indoor-panel-body";
  body.innerHTML = `
    <div class="indoor-panel-shell">
      <div class="indoor-toolbar">
        <div class="indoor-toolbar-copy">
          <span class="summary-kicker">当前建筑</span>
          <h4>${escapeHtml(activeBuilding.building_name)} · ${escapeHtml(activeFloorLabel)}</h4>
          <p>入口：${escapeHtml(activeBuilding.entry_node_name || getNodeName(activeBuilding.entry_node_id))} · 默认楼层 ${escapeHtml(floorLabelForId(activeBuilding.default_floor_id || ""))}</p>
        </div>
        <div class="card-actions card-actions-secondary">
          <button class="ghost-button" type="button" data-indoor-entry-focus="${escapeHtml(activeBuilding.entry_node_id || activeBuilding.building_id)}">定位建筑入口</button>
        </div>
      </div>
      ${renderIndoorRouteViewToggle(state.currentRoute, currentViewId)}
      ${renderIndoorFloorSwitcher(payload, activeFloorId)}
      <div class="indoor-callout">${escapeHtml(routeNotice)}</div>
      ${renderIndoorSelectedZone(selectedZone)}
      <div class="indoor-panel-controls">
        <div class="indoor-zone-list is-compact">
          ${renderIndoorZoneList(payload, routeContext, state.indoor.selectedZoneNodeId)}
        </div>
      </div>
    </div>
  `;
}

function renderIndoorEmptyState(buildings, errorMessage = "") {
  const featured = buildings.slice(0, 6);
  return `
    <div class="indoor-state-card">
      <strong>从支持建筑进入室内导航</strong>
      <p>${escapeHtml(errorMessage || "先点建筑，再进室内、选楼层、选功能区并规划路线。可先在地图上点击建筑 popup，也可以直接用下方快捷入口。")}</p>
      <ol class="quickstart-list">
        <li>点击图书馆、教学楼、宿舍等支持建筑。</li>
        <li>进入室内导航后先确认楼层，再选功能区。</li>
        <li>选中目标点后点击“规划路线”，再按需切换室内 / 室外路线视图。</li>
      </ol>
      <div class="indoor-building-chips">
        ${featured
          .map((item) => `
            <button class="ghost-button" type="button" data-enter-indoor="${escapeHtml(item.building_id)}" data-indoor-floor="${escapeHtml(item.default_floor_id || "")}">
              进入 ${escapeHtml(item.building_name)}
            </button>
          `)
          .join("")}
        <button class="ghost-button" type="button" data-show-supported-indoor="true">
          查看支持室内导航的建筑
        </button>
      </div>
    </div>
  `;
}

function renderIndoorQuickStart() {
  const status = document.querySelector("#indoor-quickstart-status");
  const actions = document.querySelector("#indoor-quick-actions");
  const supported = document.querySelector("#indoor-supported-buildings");
  if (!status || !actions || !supported) {
    return;
  }

  const buildings = state.indoor.buildings || [];
  const preferredIds = ["library", "teaching_building_1", "teaching_building", "dormitory_1"];
  const preferredBuildings = preferredIds
    .map((buildingId) => indoorBuildingRecord(buildingId))
    .filter(Boolean);
  const featuredBuildings = preferredBuildings.length
    ? preferredBuildings
    : buildings.slice(0, 3);
  const selectedZone = (state.indoor.activePayload?.zones || []).find(
    (item) => item.id === state.indoor.selectedZoneNodeId,
  );
  if (state.indoor.activeBuildingId && state.indoor.activePayload) {
    status.textContent = selectedZone
      ? `当前已进入 ${indoorBuildingRecord(state.indoor.activeBuildingId)?.building_name || getNodeName(state.indoor.activeBuildingId)} ${indoorPayloadFloorLabel(state.indoor.activePayload)}，可直接规划到 ${selectedZone.name}。`
      : `当前已进入 ${indoorBuildingRecord(state.indoor.activeBuildingId)?.building_name || getNodeName(state.indoor.activeBuildingId)} ${indoorPayloadFloorLabel(state.indoor.activePayload)}，请先选择功能区。`;
  } else {
    status.textContent = "先点建筑进入室内导航，或直接使用下方快捷入口。";
  }

  actions.innerHTML = featuredBuildings
    .map((building) => {
      let label = `进入 ${building.building_name}`;
      if (building.building_id === "library") {
        label = "进入图书馆室内导航";
      } else if (["teaching_building_1", "teaching_building"].includes(building.building_id)) {
        label = "去教学楼找教室";
      } else if (building.building_id === "dormitory_1") {
        label = "去宿舍找房间";
      }
      return `
        <button
          class="quick-chip"
          type="button"
          data-enter-indoor="${escapeHtml(building.building_id)}"
          data-indoor-floor="${escapeHtml(building.default_floor_id || "")}"
        >
          ${escapeHtml(label)}
        </button>
      `;
    })
    .concat([
      `<button class="ghost-button" type="button" data-show-supported-indoor="true">查看支持室内导航的建筑</button>`,
    ])
    .join("");

  supported.innerHTML = buildings
    .map((building) => `
      <button
        class="ghost-button indoor-supported-building"
        type="button"
        data-enter-indoor="${escapeHtml(building.building_id)}"
        data-indoor-floor="${escapeHtml(building.default_floor_id || "")}"
      >
        ${escapeHtml(building.building_name)} · ${escapeHtml((building.floor_ids || []).join(" / "))}
      </button>
    `)
    .join("");
}

function renderIndoorRouteViewToggle(route, currentViewId) {
  const views = route?.ui?.available_route_views || [];
  if (views.length <= 1) {
    return "";
  }
  return `
    <div class="indoor-route-view-switcher">
      <span class="indoor-control-label">路线视图</span>
      <div class="renderer-toggle compact-toggle">
        ${views
          .map((view) => `
            <button
              class="renderer-toggle-button${view.id === currentViewId ? " active" : ""}"
              type="button"
              data-route-view="${escapeHtml(view.id)}"
              aria-pressed="${String(view.id === currentViewId)}"
            >
              ${escapeHtml(view.label)}
            </button>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function renderIndoorFloorSwitcher(payload, activeFloorId) {
  const floors = payload?.available_floors || [];
  if (!floors.length) {
    return "";
  }
  return `
    <div class="indoor-floor-switcher">
      <span class="indoor-control-label">楼层切换</span>
      <div class="renderer-toggle compact-toggle">
        ${floors
          .map((floor) => `
            <button
              class="renderer-toggle-button${floor.floor_id === activeFloorId || floor.id === activeFloorId ? " active" : ""}"
              type="button"
              data-indoor-floor="${escapeHtml(floor.floor_id || floor.id || "")}"
              aria-pressed="${String(floor.floor_id === activeFloorId || floor.id === activeFloorId)}"
            >
              ${escapeHtml(floor.floor_label || floor.label || floorLabelForId(floor.floor_id || floor.id || ""))}
            </button>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function renderIndoorSelectedZone(selectedZone) {
  if (!selectedZone) {
    return `
      <div class="indoor-selection-card is-empty">
        <div>
          <strong>尚未选择功能区</strong>
          <p>点击平面图上的功能区点位，或在右侧列表中选择一个房间/服务区。</p>
        </div>
        <button class="route-button" type="button" data-plan-indoor-route disabled>
          规划路线
        </button>
      </div>
    `;
  }

  const facilities = Array.isArray(selectedZone.facilities) && selectedZone.facilities.length
    ? selectedZone.facilities.join(" / ")
    : "暂无设施标签";
  return `
    <div class="indoor-selection-card">
      <div>
        <strong>已选目标：${escapeHtml(selectedZone.name)}</strong>
        <p>${escapeHtml(selectedZone.description || selectedZone.category_label || "可作为本次室内导航目标点。")}</p>
        <span class="indoor-selection-meta">${escapeHtml(facilities)}</span>
      </div>
      <button class="route-button" type="button" data-plan-indoor-route>
        规划路线
      </button>
    </div>
  `;
}

function renderIndoorZoneList(payload, routeContext, selectedZoneNodeId) {
  const zones = payload?.zones || [];
  if (!zones.length) {
    return `<div class="empty-state">当前楼层没有可选功能区。</div>`;
  }
  const routeNodeIds = new Set(routeContext?.floorView?.route_node_ids || []);
  return zones
    .map((zone, index) => {
      const isSelected = zone.id === selectedZoneNodeId;
      const isRoute = routeNodeIds.has(zone.id);
      const facilities = Array.isArray(zone.facilities) && zone.facilities.length
        ? zone.facilities.join(" / ")
        : (zone.tags || []).join(" / ");
      return `
        <article class="indoor-zone-card${isSelected ? " active" : ""}${isRoute ? " is-route" : ""}" style="animation-delay: ${index * 0.03}s">
          <button class="indoor-zone-select" type="button" data-indoor-zone="${escapeHtml(zone.id)}">
            <span>${escapeHtml(zone.name)}</span>
            <span class="metric-pill">${escapeHtml(zone.floor_label || "")}</span>
          </button>
          <p>${escapeHtml(zone.description || zone.category_label || "可作为目标点。")}</p>
          ${facilities ? `<span class="indoor-zone-meta">${escapeHtml(facilities)}</span>` : ""}
          <div class="card-actions card-actions-secondary">
            <button class="ghost-button" type="button" data-indoor-zone="${escapeHtml(zone.id)}">选中</button>
            <button class="route-button" type="button" data-indoor-route-target="${escapeHtml(zone.id)}">规划路线</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function indoorEdgeKey(fromNodeId, toNodeId) {
  return [fromNodeId, toNodeId].sort().join("::");
}

function renderIndoorFloorplan(payload, options = {}) {
  const floorplan = payload?.floorplan;
  if (floorplan?.renderer === "svg_floorplan" && Array.isArray(floorplan.rooms)) {
    return renderIndoorSvgFloorplan(payload, floorplan, options);
  }
  return renderIndoorNetworkFloorplan(payload, options);
}

function renderIndoorSvgFloorplan(payload, floorplan, options = {}) {
  const nodes = Array.isArray(payload?.nodes) ? payload.nodes : [];
  const routeContext = options.routeContext?.floorView || null;
  const shouldHighlightRoute = Boolean(routeContext) && options.currentViewId !== "outdoor";
  const routeNodeIds = new Set(shouldHighlightRoute ? (routeContext.route_node_ids || []) : []);
  const routeEdgeKeys = new Set(
    shouldHighlightRoute
      ? (routeContext.path_segments || []).map((segment) => indoorEdgeKey(segment.from, segment.to))
      : [],
  );
  const selectedZoneNodeId = options.selectedZoneNodeId || "";
  const nodeLookup = {};
  nodes.forEach((node) => {
    nodeLookup[node.id] = node;
  });

  const viewBox = floorplan.view_box || { x: 0, y: 0, width: 360, height: 260 };
  const viewBoxText = [
    svgNumber(viewBox.x),
    svgNumber(viewBox.y),
    svgNumber(viewBox.width),
    svgNumber(viewBox.height),
  ].join(" ");

  const corridors = Array.isArray(floorplan.corridors) ? floorplan.corridors : [];
  const corridorByEdgeKey = {};
  corridors.forEach((corridor) => {
    if (corridor.edge_key) {
      corridorByEdgeKey[corridor.edge_key] = corridor;
    }
  });

  const shellMarkup = floorplan.outer_shell?.polygon
    ? `<polygon class="indoor-floor-shell" points="${svgPoints(floorplan.outer_shell.polygon)}"></polygon>`
    : "";

  const corridorMarkup = corridors
    .map((corridor) => {
      const isRoute = routeEdgeKeys.has(corridor.edge_key);
      const corridorPath = indoorCorridorPath(corridor);
      return `
        <polyline
          class="indoor-floor-corridor${isRoute ? " is-route" : ""}"
          points="${svgPoints(corridorPath)}"
          style="--corridor-width: ${svgNumber(corridor.width || 44)}"
        ></polyline>
      `;
    })
    .join("");

  const roomMarkup = (floorplan.rooms || [])
    .map((room) => {
      const node = nodeLookup[room.node_id] || {};
      const isZone = isIndoorZoneNode(node);
      const isSelected = room.node_id === selectedZoneNodeId;
      const isRoute = routeNodeIds.has(room.node_id);
      const className = [
        "indoor-floor-room",
        room.zone_type ? `is-${room.zone_type}` : "",
        isZone ? "is-zone" : "",
        isSelected ? "is-selected" : "",
        isRoute ? "is-route" : "",
        room.is_gate ? "is-gate" : "",
      ]
        .filter(Boolean)
        .join(" ");
      return `
        <g class="${escapeHtml(className)}" ${isZone ? `data-indoor-zone="${escapeHtml(room.node_id)}"` : ""}>
          <polygon points="${svgPoints(room.polygon)}"></polygon>
          <title>${escapeHtml(room.name || room.node_id)}</title>
        </g>
      `;
    })
    .join("");

  const wallMarkup = (floorplan.walls || [])
    .map((wall) => `
      <line
        class="indoor-floor-wall${wall.wall_type === "outer" ? " is-outer" : ""}"
        x1="${svgNumber(wall.points?.[0]?.[0])}"
        y1="${svgNumber(wall.points?.[0]?.[1])}"
        x2="${svgNumber(wall.points?.[1]?.[0])}"
        y2="${svgNumber(wall.points?.[1]?.[1])}"
      ></line>
    `)
    .join("");

  const doorMarkup = (floorplan.doors || [])
    .map((door) => `
      <line
        class="indoor-floor-door"
        x1="${svgNumber(door.segment?.[0]?.[0])}"
        y1="${svgNumber(door.segment?.[0]?.[1])}"
        x2="${svgNumber(door.segment?.[1]?.[0])}"
        y2="${svgNumber(door.segment?.[1]?.[1])}"
      ></line>
    `)
    .join("");

  const routeMarkup = shouldHighlightRoute
    ? (routeContext.path_segments || [])
        .map((segment) => {
          const corridor = corridorByEdgeKey[indoorEdgeKey(segment.from, segment.to)];
          const points = indoorCorridorPath(corridor);
          if (!points?.[0] || !points?.[1]) {
            return "";
          }
          return `
            <polyline
              class="indoor-route-overlay"
              points="${svgPoints(points)}"
            ></polyline>
          `;
        })
        .join("")
    : "";

  const iconMarkup = (floorplan.icons || [])
    .map((icon) => renderIndoorFloorplanIcon(icon, {
      isSelected: icon.node_id === selectedZoneNodeId,
      isRoute: routeNodeIds.has(icon.node_id),
    }))
    .join("");

  const labelMarkup = (floorplan.labels || [])
    .map((label) => {
      const isSelected = label.node_id === selectedZoneNodeId;
      const isRoute = routeNodeIds.has(label.node_id);
      return `
        <text
          class="indoor-floor-label${isSelected ? " is-selected" : ""}${isRoute ? " is-route" : ""}"
          x="${svgNumber(label.x)}"
          y="${svgNumber(label.y)}"
        >
          ${escapeHtml(indoorFloorplanLabel(label.text))}
        </text>
      `;
    })
    .join("");

  return `
    <svg
      class="indoor-floorplan is-realistic"
      viewBox="${viewBoxText}"
      role="img"
      aria-label="${escapeHtml(payload.building_name || payload.building_id || "室内平面图")} ${escapeHtml(indoorPayloadFloorLabel(payload))}"
    >
      <g class="indoor-floor-realistic">
        ${shellMarkup}
        <g class="indoor-floor-corridors">${corridorMarkup}</g>
        <g class="indoor-floor-rooms">${roomMarkup}</g>
        <g class="indoor-floor-walls">${wallMarkup}</g>
        <g class="indoor-floor-doors">${doorMarkup}</g>
        <g class="indoor-floor-route">${routeMarkup}</g>
        <g class="indoor-floor-icons">${iconMarkup}</g>
        <g class="indoor-floor-labels">${labelMarkup}</g>
      </g>
    </svg>
  `;
}

function renderIndoorNetworkFloorplan(payload, options = {}) {
  const nodes = Array.isArray(payload?.nodes) ? payload.nodes : [];
  const edges = Array.isArray(payload?.edges) ? payload.edges : [];
  const layoutNodes = nodes.filter((node) => Number.isFinite(node?.layout?.x) && Number.isFinite(node?.layout?.y));
  if (!layoutNodes.length) {
    return `<div class="indoor-floorplan-empty">当前楼层缺少可渲染的平面图坐标。</div>`;
  }

  const nodeLookup = {};
  layoutNodes.forEach((node) => {
    nodeLookup[node.id] = node;
  });

  const routeContext = options.routeContext?.floorView || null;
  const shouldHighlightRoute = Boolean(routeContext) && options.currentViewId !== "outdoor";
  const routeNodeIds = new Set(shouldHighlightRoute ? (routeContext.route_node_ids || []) : []);
  const routeEdgeKeys = new Set(
    shouldHighlightRoute
      ? (routeContext.path_segments || []).map((segment) => indoorEdgeKey(segment.from, segment.to))
      : [],
  );
  const selectedZoneNodeId = options.selectedZoneNodeId || "";
  const padding = 48;
  const xValues = layoutNodes.map((node) => Number(node.layout.x));
  const yValues = layoutNodes.map((node) => Number(node.layout.y));
  const minX = Math.min(...xValues) - padding;
  const minY = Math.min(...yValues) - padding;
  const width = Math.max(Math.max(...xValues) - Math.min(...xValues) + padding * 2, 320);
  const height = Math.max(Math.max(...yValues) - Math.min(...yValues) + padding * 2, 240);

  const edgeMarkup = edges
    .map((edge) => {
      const fromNode = nodeLookup[edge.from];
      const toNode = nodeLookup[edge.to];
      if (!fromNode || !toNode) {
        return "";
      }
      const isRoute = routeEdgeKeys.has(indoorEdgeKey(edge.from, edge.to));
      return `
        <line
          class="indoor-floor-edge${isRoute ? " is-route" : ""}"
          x1="${Number(fromNode.layout.x)}"
          y1="${Number(fromNode.layout.y)}"
          x2="${Number(toNode.layout.x)}"
          y2="${Number(toNode.layout.y)}"
        ></line>
      `;
    })
    .join("");

  const nodeMarkup = layoutNodes
    .map((node) => {
      const x = Number(node.layout.x);
      const y = Number(node.layout.y);
      const isZone = isIndoorZoneNode(node);
      const isSelected = node.id === selectedZoneNodeId;
      const isRoute = routeNodeIds.has(node.id);
      const className = [
        "indoor-floor-node",
        isZone ? "is-zone" : "is-passage",
        isSelected ? "is-selected" : "",
        isRoute ? "is-route" : "",
        node.is_gate ? "is-gate" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const marker = isZone
        ? `<circle cx="${x}" cy="${y}" r="14"></circle>`
        : `<rect x="${x - 10}" y="${y - 10}" width="20" height="20" rx="6" ry="6"></rect>`;
      const labelText = node.name || node.id;
      const labelY = isZone ? y + 28 : y + 24;
      return `
        <g class="${className}" ${isZone ? `data-indoor-zone="${escapeHtml(node.id)}"` : ""}>
          ${marker}
          <text x="${x}" y="${labelY}">${escapeHtml(labelText)}</text>
        </g>
      `;
    })
    .join("");

  return `
    <svg
      class="indoor-floorplan"
      viewBox="${minX} ${minY} ${width} ${height}"
      role="img"
      aria-label="${escapeHtml(payload.building_name || payload.building_id || "室内平面图")} ${escapeHtml(indoorPayloadFloorLabel(payload))}"
    >
      <g class="indoor-floor-grid">
        ${edgeMarkup}
        ${nodeMarkup}
      </g>
    </svg>
  `;
}

function indoorCorridorPath(corridor) {
  if (Array.isArray(corridor?.path) && corridor.path.length >= 2) {
    return corridor.path;
  }
  if (Array.isArray(corridor?.segment) && corridor.segment.length >= 2) {
    return corridor.segment;
  }
  return [];
}

function renderIndoorFloorplanIcon(icon, stateFlags = {}) {
  const iconType = icon?.type || "area";
  const label = indoorFloorplanIconLabel(iconType);
  const className = [
    "indoor-floor-icon",
    iconType ? `is-${iconType}` : "",
    stateFlags.isSelected ? "is-selected" : "",
    stateFlags.isRoute ? "is-route" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return `
    <g class="${escapeHtml(className)}" transform="translate(${svgNumber(icon?.x)}, ${svgNumber(icon?.y)})">
      <circle cx="0" cy="0" r="12"></circle>
      <text x="0" y="4">${escapeHtml(label)}</text>
    </g>
  `;
}

function indoorFloorplanIconLabel(iconType) {
  const labels = {
    restroom: "WC",
    elevator: "EL",
    stairs: "ST",
    lobby: "IN",
    reading_room: "阅",
    classroom: "课",
    dormitory: "寝",
    catering: "餐",
    sports: "体",
    service: "i",
    area: "·",
  };
  return labels[iconType] || labels.area;
}

function indoorFloorplanLabel(text) {
  const value = String(text || "");
  return value.length > 12 ? `${value.slice(0, 11)}...` : value;
}

function svgPoints(points) {
  if (!Array.isArray(points)) {
    return "";
  }
  return points.map((point) => `${svgNumber(point?.[0])},${svgNumber(point?.[1])}`).join(" ");
}

function svgNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "0";
  }
  return String(Math.round(number * 100) / 100);
}

function renderMetricPill(text, className = "") {
  if (!text) {
    return "";
  }
  return `<span class="metric-pill ${className}">${escapeHtml(text)}</span>`;
}

function renderSingleRouteStep(step, index) {
  const edgeName = step.edge_name ? ` · ${escapeHtml(step.edge_name)}` : "";
  return `
    <article class="step-card" style="animation-delay: ${index * 0.03}s">
      <h4>第 ${step.step_index} 步${edgeName}</h4>
      <p>${escapeHtml(step.from_node_name)} -> ${escapeHtml(step.to_node_name)}</p>
      <div class="card-metrics">
        ${renderMetricPill(step.display_layer || step.to_layer || "")}
        ${renderMetricPill(formatDistance(step.distance_m, "available"))}
        ${renderMetricPill(formatSeconds(step.estimated_time_s))}
        ${renderMetricPill(step.transition_kind === "cross_layer" ? "跨层" : "同层")}
      </div>
      <p>${escapeHtml(step.description || "沿当前道路继续前进。")}</p>
    </article>
  `;
}

function renderStepDetails(label, contentMarkup) {
  if (!contentMarkup) {
    return "暂无步骤";
  }
  return `
    <details class="route-step-details">
      <summary>${escapeHtml(label)}</summary>
      <div class="route-step-detail-list">
        ${contentMarkup}
      </div>
    </details>
  `;
}

function routePrimarySentence(route) {
  if (route.route_type === "multi_target") {
    const summary = route.summary || {};
    return `已按访问顺序完成 ${summary.leg_count || 0} 段路线。`;
  }

  const names = route.path_node_names || [];
  const via = names.length > 2 ? `，途经 ${names.slice(1, -1).slice(0, 3).join("、")}` : "";
  return `已完成从 ${route.start_node_name} 到 ${route.target_node_name} 的路线${via}。`;
}

function routeGeometryStats(route = state.currentRoute) {
  return route?.ui?.route_geometry_stats || null;
}

function routeGeometryCoverageRatio(route = state.currentRoute) {
  const stats = routeGeometryStats(route);
  const total = Number(stats?.route_segment_count) || 0;
  if (!total) {
    return 0;
  }
  return (Number(stats.geometry_segment_count) || 0) / total;
}

function routeGeometrySummaryText(route = state.currentRoute) {
  const stats = routeGeometryStats(route);
  const total = Number(stats?.route_segment_count) || 0;
  if (!total) {
    return "";
  }

  const geometryCount = Number(stats.geometry_segment_count) || 0;
  const osmMatchedCount = Number(stats.osm_matched_segment_count) || 0;
  const manualCount = Number(stats.manual_geometry_segment_count) || Math.max(0, geometryCount - osmMatchedCount);
  const fallbackCount = Number(stats.fallback_segment_count) || 0;
  const missingEdgeCount = Number(stats.missing_edge_count) || 0;
  return `真实路线 ${geometryCount}/${total} 段 · OSM匹配 ${osmMatchedCount} · manual ${manualCount} · fallback ${fallbackCount} · missing ${missingEdgeCount} · ${formatRatioPercent(routeGeometryCoverageRatio(route))}`;
}

function appendRouteGeometryCaption(captionText, route = state.currentRoute) {
  const geometrySummary = routeGeometrySummaryText(route);
  return geometrySummary ? `${captionText} ${geometrySummary}。` : captionText;
}

function selectedMapRenderer() {
  if (!state.bootstrap) {
    return "simple_svg";
  }

  const renderers = availableMapRenderers();
  const capabilities = state.bootstrap.map_capabilities || {};
  const renderer = state.mapRenderer || state.bootstrap.map_renderer || capabilities.default_renderer || "simple_svg";
  return renderers.includes(renderer) ? renderer : "simple_svg";
}

function hasIndoorMapContext() {
  const payload = state.indoor.activePayload;
  return Boolean(
    state.indoor.activeBuildingId
    && payload
    && payload.building_id === state.indoor.activeBuildingId,
  );
}

function selectedMapViewMode() {
  return hasIndoorMapContext() && state.indoor.mapMode === "indoor" ? "indoor" : "outdoor";
}

function currentRouteHasView(viewId) {
  return Boolean((state.currentRoute?.ui?.available_route_views || []).some((view) => view.id === viewId));
}

function rememberIndoorRouteViewId(viewId) {
  if (!viewId || viewId === "outdoor" || !parseIndoorRouteViewId(viewId)) {
    return;
  }
  state.indoor.lastIndoorRouteViewId = viewId;
}

function resolveActiveIndoorRouteViewId() {
  if (!hasIndoorMapContext()) {
    return "";
  }

  const activeBuildingId = state.indoor.activeBuildingId;
  const activeFloorId = state.indoor.activeFloorId || indoorPayloadFloorId(state.indoor.activePayload);
  const fallbackViewId = indoorRouteViewId(activeBuildingId, activeFloorId);
  const candidates = [
    state.indoor.currentRouteViewId,
    state.indoor.lastIndoorRouteViewId,
    state.currentRoute?.ui?.default_route_view,
    fallbackViewId,
  ];

  for (const viewId of candidates) {
    const parsed = parseIndoorRouteViewId(viewId);
    if (parsed?.buildingId === activeBuildingId && parsed.floorId === activeFloorId) {
      return viewId;
    }
  }
  return fallbackViewId;
}

function switchIndoorOutdoorMapView(mode, options = {}) {
  if (mode === "indoor") {
    if (!hasIndoorMapContext()) {
      if (!options.silentStatus) {
        setStatus("请先进入支持建筑的室内导航。", "error");
      }
      syncMapViewToggle();
      return;
    }

    const indoorViewId = resolveActiveIndoorRouteViewId();
    state.indoor.mapMode = "indoor";
    state.indoor.currentRouteViewId = indoorViewId;
    rememberIndoorRouteViewId(indoorViewId);
    renderIndoorPanel();
    renderMap();
    if (!options.silentStatus) {
      setStatus("已切换到室内视图。", "info");
    }
    return;
  }

  state.indoor.mapMode = "outdoor";
  if (currentRouteHasView("outdoor")) {
    state.indoor.currentRouteViewId = "outdoor";
  }
  renderIndoorPanel();
  renderMap();
  if (!options.silentStatus) {
    setStatus("已切换到室外视图。", "info");
  }
}

function toggleIndoorOutdoorMapView() {
  switchIndoorOutdoorMapView(selectedMapViewMode() === "indoor" ? "outdoor" : "indoor");
}

function syncMapViewToggle() {
  const button = document.querySelector("#map-view-toggle");
  if (!button) {
    return;
  }

  const hasIndoorContext = hasIndoorMapContext();
  const isIndoorView = selectedMapViewMode() === "indoor";
  button.hidden = !hasIndoorContext;
  button.textContent = isIndoorView ? "室外视图" : "室内视图";
  button.setAttribute("aria-label", isIndoorView ? "切换到室外视图" : "切换到室内视图");
  button.setAttribute("aria-pressed", String(isIndoorView));
  button.classList.toggle("active", isIndoorView);
}

function availableMapRenderers() {
  const capabilities = state.bootstrap?.map_capabilities || {};
  return Array.isArray(capabilities.renderers) ? capabilities.renderers : ["simple_svg"];
}

function basemapCapabilities(bootstrap = state.bootstrap) {
  return bootstrap?.map_capabilities?.basemaps || {};
}

function availableBasemapModes() {
  const modes = basemapCapabilities().modes;
  return Array.isArray(modes) ? modes.filter((mode) => mode && mode.id) : [];
}

function defaultBasemapMode(bootstrap = state.bootstrap) {
  const basemaps = basemapCapabilities(bootstrap);
  const defaultMode = basemaps.default || "real_map";
  const modes = Array.isArray(basemaps.modes) ? basemaps.modes : [];
  return modes.some((mode) => mode.id === defaultMode) ? defaultMode : "none";
}

function resolveBasemapMode(mode) {
  const requestedMode = mode || state.basemapMode || defaultBasemapMode();
  const modes = availableBasemapModes();
  if (modes.some((item) => item.id === requestedMode)) {
    return requestedMode;
  }

  const fallbackMode = basemapCapabilities().fallback || "none";
  if (modes.some((item) => item.id === fallbackMode)) {
    return fallbackMode;
  }
  return modes.length ? modes[0].id : "";
}

function selectedBasemapMode() {
  return resolveBasemapMode(state.basemapMode) || "none";
}

function basemapConfig(mode = selectedBasemapMode()) {
  return availableBasemapModes().find((item) => item.id === mode) || null;
}

function basemapModeLabel(mode = selectedBasemapMode()) {
  return basemapConfig(mode)?.label || mode || "无底图";
}

function basemapTileSources(mode = selectedBasemapMode()) {
  const config = basemapConfig(mode);
  if (!config) {
    return [];
  }
  if (Array.isArray(config.tile_sources) && config.tile_sources.length) {
    return config.tile_sources.filter((source) => source && source.tile_url);
  }
  if (config.tile_url) {
    return [{
      id: config.id || mode,
      label: config.label || mode,
      tile_url: config.tile_url,
      attribution: config.attribution || "",
      source: config.source || config.label || mode,
      subdomains: config.subdomains || "",
    }];
  }
  return [];
}

function selectedBasemapTileSource(mode = selectedBasemapMode()) {
  const sources = basemapTileSources(mode);
  if (!sources.length) {
    return null;
  }
  const boundedIndex = Math.max(0, Math.min(state.basemapSourceIndex || 0, sources.length - 1));
  state.basemapSourceIndex = boundedIndex;
  return sources[boundedIndex];
}

function fallbackBasemapMode() {
  return resolveBasemapMode(basemapCapabilities().fallback || "none") || "none";
}

function basemapCaptionPrefix() {
  const config = basemapConfig();
  const tileSource = selectedBasemapTileSource();
  if (!config || !tileSource) {
    const errorText = state.basemapError ? `${state.basemapError} ` : "";
    return `${errorText}无底图模式：项目道路、POI 和路线来自本地 GeoJSON。`;
  }

  const networkText = config.network_required ? "需联网加载瓦片" : "无网络依赖";
  const sourceText = tileSource.source || tileSource.label || config.source || config.label;
  const errorText = state.basemapError ? ` ${state.basemapError}` : "";
  return `真实底图：${sourceText}（${networkText}）；项目道路、POI 和路线来自本地 GeoJSON。${errorText}`;
}

function availableOsmLayerConfigs() {
  const layers = state.bootstrap?.map_capabilities?.osm_layers?.layers;
  return Array.isArray(layers) ? layers.filter((layer) => layer && layer.id) : [];
}

function defaultOsmLayerVisibility(bootstrap = state.bootstrap) {
  const defaults = bootstrap?.map_capabilities?.osm_layers?.default_visible || {};
  const visibility = {};
  availableOsmLayerConfigsForBootstrap(bootstrap).forEach((layer) => {
    visibility[layer.id] = defaults[layer.id] !== false;
  });
  return {
    roads: visibility.roads !== false,
    buildings: visibility.buildings !== false,
    water_landuse: visibility.water_landuse !== false,
    ...visibility,
  };
}

function defaultWhiteRoadRoleVisibility() {
  return {
    junction: true,
    bend: true,
    endpoint: true,
    poi_access: true,
  };
}

function isPathNodeData(node) {
  return Boolean(
    node?.is_waypoint
    || node?.display_role === "waypoint"
    || node?.category === "road",
  );
}

function isPathNodeFeature(feature) {
  return isPathNodeData(feature?.properties || {});
}

function availableOsmLayerConfigsForBootstrap(bootstrap) {
  const layers = bootstrap?.map_capabilities?.osm_layers?.layers;
  return Array.isArray(layers) ? layers.filter((layer) => layer && layer.id) : [];
}

function osmLayerLabel(layerId) {
  return availableOsmLayerConfigs().find((layer) => layer.id === layerId)?.label || layerId;
}

function renderMap() {
  if (state.activePage !== "app") {
    return;
  }
  const renderToken = state.mapRenderToken + 1;
  state.mapRenderToken = renderToken;
  syncMapDemoPanel();
  syncIndoorMapStage();
  if (selectedMapViewMode() === "indoor") {
    setMapRendererVisibility(selectedMapRenderer());
    return;
  }
  if (selectedMapRenderer() === "leaflet_geo") {
    void renderLeafletMap(renderToken);
    return;
  }
  renderSvgMap("", renderToken);
}

function renderSvgMap(fallbackMessage = "", renderToken = state.mapRenderToken) {
  if (renderToken !== state.mapRenderToken) {
    return;
  }

  const svg = document.querySelector("#campus-map");
  const caption = document.querySelector("#map-caption") || { textContent: '' };
  setMapRendererVisibility("simple_svg");

  if (!state.bootstrap) {
    svg.innerHTML = "";
    caption.textContent = "地图尚未加载。";
    return;
  }

  const mapData = state.bootstrap.map;
  const routePath = state.currentRoute?.ui?.mappable_path_node_ids || [];
  const highlightNodeIds = getMapHighlightNodeIds();

  const projectedNodes = new Map(
    mapData.nodes.map((node) => [node.id, projectNode(node, mapData.bounds)]),
  );
  const screenNodes = new Map(
    Array.from(projectedNodes.entries()).map(([nodeId, point]) => [
      nodeId,
      transformMapPoint(point),
    ]),
  );

  const edgeMarkup = mapData.edges
    .map((edge) => {
      const from = projectedNodes.get(edge.from);
      const to = projectedNodes.get(edge.to);
      if (!from || !to) {
        return "";
      }
      return `<line class="edge-line" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />`;
    })
    .join("");

  const routeMarkup = routePath.length >= 2
    ? `<polyline class="route-line" points="${routePath
        .map((nodeId) => {
          const point = projectedNodes.get(nodeId);
          return point ? `${point.x},${point.y}` : "";
        })
        .filter(Boolean)
        .join(" ")}" />`
    : "";

  const visibleNodes = mapData.nodes.filter((node) => state.pathNodesVisible || !isPathNodeData(node));
  const nodeMarkup = visibleNodes
    .map((node) => {
      const projected = screenNodes.get(node.id);
      const fill = colorForCategory(node.category);
      const isHighlighted = highlightNodeIds.has(node.id);
      const isWaypoint = isPathNodeData(node);
      const radius = isHighlighted ? 12 : isWaypoint ? 4 : node.category === "entrance" ? 9 : 7;
      const labelDy = isWaypoint ? 0 : 20;
      const showLabel = !isWaypoint && node.show_label !== false;
      const labelText = showLabel ? escapeHtml(node.name) : "";
      const labelWidth = estimateLabelWidth(node.name);
      const labelX = projected.x - labelWidth / 2;
      const labelY = projected.y + labelDy - 14;
      return `
        <g class="svg-map-node${isHighlighted ? " is-highlighted" : ""}" data-map-node="${escapeHtml(node.id)}">
          ${isHighlighted ? `<circle class="route-dot" cx="${projected.x}" cy="${projected.y}" r="${radius + 6}" fill="rgba(181, 94, 59, 0.16)" />` : ""}
          <circle cx="${projected.x}" cy="${projected.y}" r="${radius}" fill="${fill}" stroke="white" stroke-width="${isWaypoint ? 2 : 3}" opacity="${isWaypoint && !isHighlighted ? 0.48 : 1}" />
          ${
            showLabel
              ? `
                <rect class="node-label-bg" x="${labelX}" y="${labelY}" width="${labelWidth}" height="19" rx="8" />
                <text class="node-label" x="${projected.x}" y="${projected.y + labelDy}" text-anchor="middle">${labelText}</text>
              `
              : ""
          }
        </g>
      `;
    })
    .join("");

  const legendMarkup = `
    <g transform="translate(44, 54)">
      <text class="legend-badge" x="0" y="0">室外校园简图</text>
      <text class="legend-badge" x="0" y="28" style="font-size: 14px; fill: rgba(29, 43, 56, 0.58);">
        高亮橙线为当前路径；滚轮缩放，按住拖动平移
      </text>
    </g>
  `;
  const mapTransform = `translate(${state.mapView.translateX} ${state.mapView.translateY}) scale(${state.mapView.scale})`;

  svg.innerHTML = `
    <rect x="0" y="0" width="${MAP_WIDTH}" height="${MAP_HEIGHT}" fill="transparent" />
    ${legendMarkup}
    <g transform="${mapTransform}">
      ${edgeMarkup}
      ${routeMarkup}
      </g>
    ${nodeMarkup}
  `;

  const captionText = state.currentRoute
    ? appendRouteGeometryCaption(state.currentRoute.ui.caption)
    : state.focusedNodeId
      ? `当前已定位 ${getNodeName(state.focusedNodeId)}，可继续规划路线或进入楼内视图。`
      : state.pathNodesVisible
        ? `当前展示室外地点与路网点；缩放 ${Math.round(state.mapView.scale * 100)}%，可拖动查看细节。`
        : `当前优先展示可导航地点，路径节点默认收起；缩放 ${Math.round(state.mapView.scale * 100)}%，可拖动查看细节。`;
  caption.textContent = fallbackMessage ? `${fallbackMessage} ${captionText}` : captionText;
  syncMapDemoPanel();
}

async function renderLeafletMap(renderToken = state.mapRenderToken) {
  const caption = document.querySelector("#map-caption") || { textContent: '' };
  if (renderToken !== state.mapRenderToken) {
    return;
  }

  if (!state.bootstrap) {
    setMapRendererVisibility("leaflet_geo");
    caption.textContent = "地图尚未加载。";
    syncMapDemoPanel();
    return;
  }

  try {
    setMapRendererVisibility("leaflet_geo");
    ensureLeafletMap();
    syncLeafletBasemapLayer();
    caption.textContent = `${basemapCaptionPrefix()} 正在加载 GeoJSON...`;

    const geojson = await loadMapGeoJson();
    const osmPayload = await loadOsmLayersSafely();
    if (renderToken !== state.mapRenderToken || selectedMapRenderer() !== "leaflet_geo") {
      return;
    }

    syncLeafletBasemapLayer();
    syncLeafletOsmLayers(osmPayload);
    syncLeafletBaseLayers(geojson);
    syncLeafletRouteLayer();
    syncLeafletLayerOrder();
    invalidateLeafletSize();

    syncLeafletCaption();
    syncMapDemoPanel();
  } catch (error) {
    fallbackToSvgMap(error);
  }
}

function syncLeafletCaption() {
  const caption = document.querySelector("#map-caption") || { textContent: '' };
  if (!caption || selectedMapRenderer() !== "leaflet_geo") {
    return;
  }

  const stats = state.mapGeoJsonStats || {};
  const osmText = osmLayerCaptionText();
  const poiCount = stats.poi_node_count ?? 0;
  const waypointCount = stats.waypoint_node_count ?? 0;
  const siteName = state.bootstrap?.site?.name || "当前站点";
  const defaultCaption = state.pathNodesVisible
    ? `当前已进入 ${siteName} 主地图，展示 ${poiCount} 个地点与 ${waypointCount} 个路网点。${basemapCaptionPrefix()} ${osmText}`
    : `当前已进入 ${siteName} 主地图，优先展示 ${poiCount} 个可导航地点。${basemapCaptionPrefix()} ${osmText}`;
  caption.textContent = state.currentRoute
    ? `${appendRouteGeometryCaption(state.currentRoute.ui.caption)} ${basemapCaptionPrefix()} ${osmText}`
    : state.focusedNodeId
      ? `当前定位 ${getNodeName(state.focusedNodeId)}。${basemapCaptionPrefix()} ${osmText}`
      : defaultCaption;
}

function ensureLeafletMap() {
  if (!window.L) {
    throw new Error("本地 Leaflet 运行库未加载");
  }

  const element = document.querySelector("#leaflet-map");
  if (!element) {
    throw new Error("Leaflet 地图容器缺失");
  }

  if (!state.leaflet.map) {
    const center = mapCenterLatLng();
    state.leaflet.map = L.map(element, {
      attributionControl: true,
      preferCanvas: true,
      worldCopyJump: false,
    }).setView(center, 17);
    fitLeafletToSiteBounds();
  }

  return state.leaflet.map;
}

async function loadMapGeoJson() {
  const siteId = currentSiteId();
  if (state.mapGeoJson && state.mapGeoJsonSiteId === siteId) {
    return state.mapGeoJson;
  }
  if (state.mapGeoJsonLoading) {
    return state.mapGeoJsonLoading;
  }

  const endpoint = state.bootstrap.map_capabilities?.geojson_endpoint || "/api/map/geojson";
  const separator = endpoint.includes("?") ? "&" : "?";
  const url = `${endpoint}${separator}site_id=${encodeURIComponent(siteId)}`;
  const loading = apiGet(url)
    .then((payload) => {
      if (!payload.success || !payload.geojson || payload.geojson.type !== "FeatureCollection") {
        throw new Error(payload.message || "GeoJSON 响应格式无效");
      }
      if (currentSiteId() === siteId) {
        state.mapGeoJson = payload.geojson;
        state.mapGeoJsonStats = payload.stats || {};
        state.mapGeoJsonSiteId = siteId;
      }
      return payload.geojson;
    })
    .finally(() => {
      if (state.mapGeoJsonLoading === loading) {
        state.mapGeoJsonLoading = null;
      }
    });
  state.mapGeoJsonLoading = loading;
  return state.mapGeoJsonLoading;
}

async function loadOsmLayersSafely() {
  try {
    return await loadOsmLayers();
  } catch (error) {
    state.osmLayerError = `本地 OSM 图层加载失败：${error.message}`;
    syncMapDemoPanel();
    setStatus(`${state.osmLayerError}；项目地图和路线不受影响。`, "error");
    return null;
  }
}

async function loadOsmLayers() {
  const siteId = currentSiteId();
  if (state.osmLayers && state.osmLayersSiteId === siteId) {
    return state.osmLayers;
  }
  if (state.osmLayersLoading) {
    return state.osmLayersLoading;
  }

  const endpoint = state.bootstrap.map_capabilities?.osm_layers_endpoint || "/api/map/osm-layers";
  const separator = endpoint.includes("?") ? "&" : "?";
  const url = `${endpoint}${separator}site_id=${encodeURIComponent(siteId)}`;
  const loading = apiGet(url)
    .then((payload) => {
      if (!payload.success || !payload.layers || typeof payload.layers !== "object") {
        throw new Error(payload.message || "本地 OSM 图层响应格式无效");
      }
      if (currentSiteId() === siteId) {
        state.osmLayers = payload;
        state.osmLayersStats = payload.stats || {};
        state.osmLayersMetadata = payload.metadata || {};
        state.osmLayersSiteId = siteId;
        state.osmLayerError = Array.isArray(payload.warnings) && payload.warnings.length
          ? `本地 OSM 图层有 ${payload.warnings.length} 条读取提示`
          : "";
      }
      return payload;
    })
    .finally(() => {
      if (state.osmLayersLoading === loading) {
        state.osmLayersLoading = null;
      }
    });
  state.osmLayersLoading = loading;
  return state.osmLayersLoading;
}

function syncLeafletBasemapLayer() {
  const map = state.leaflet.map;
  if (!map) {
    return;
  }

  const mode = selectedBasemapMode();
  const config = basemapConfig(mode);
  const tileSource = selectedBasemapTileSource(mode);
  const sourceId = tileSource?.id || "";
  if (
    state.leaflet.tileLayerMode === mode
    && state.leaflet.tileLayerSourceId === sourceId
    && (mode === "none" || state.leaflet.tileLayer)
  ) {
    return;
  }

  removeLeafletLayer("tileLayer");
  state.leaflet.tileLayerMode = mode;
  state.leaflet.tileLayerSourceId = sourceId;

  if (!config || !tileSource?.tile_url) {
    return;
  }

  const tileLayer = L.tileLayer(tileSource.tile_url, {
    attribution: tileSource.attribution || config.attribution || "",
    maxZoom: config.max_zoom || 19,
    minZoom: config.min_zoom || 0,
    subdomains: tileSource.subdomains || config.subdomains || "abc",
  });
  tileLayer.on("tileerror", () => {
    if (
      state.leaflet.tileLayer !== tileLayer
      || state.leaflet.tileLayerMode !== mode
      || state.leaflet.tileLayerSourceId !== sourceId
    ) {
      return;
    }
    switchToNextBasemapTileSource(mode, tileSource);
  });
  tileLayer.addTo(map);
  tileLayer.bringToBack();
  state.leaflet.tileLayer = tileLayer;
}

function switchToNextBasemapTileSource(mode, failedSource) {
  const sources = basemapTileSources(mode);
  const currentIndex = sources.findIndex((source) => source.id === failedSource?.id);
  const nextIndex = currentIndex >= 0 ? currentIndex + 1 : (state.basemapSourceIndex || 0) + 1;

  removeLeafletLayer("tileLayer");
  if (nextIndex < sources.length) {
    const nextSource = sources[nextIndex];
    state.basemapSourceIndex = nextIndex;
    state.basemapError = `真实底图源 ${failedSource?.label || failedSource?.id || "当前源"} 加载失败，正在切换到 ${nextSource.label || nextSource.id}。`;
    state.leaflet.tileLayerMode = "";
    state.leaflet.tileLayerSourceId = "";
    syncLeafletBasemapLayer();
    syncMapDemoPanel();
    syncLeafletCaption();
    setStatus(state.basemapError, "info");
    return;
  }

  const fallbackMode = fallbackBasemapMode();
  state.basemapMode = fallbackMode;
  state.basemapSourceIndex = 0;
  state.basemapError = `所有真实底图瓦片源暂时不可达，已切换到 ${basemapModeLabel(fallbackMode)}；本地 GeoJSON 道路、POI 和路线仍可继续显示。`;
  state.leaflet.tileLayerMode = fallbackMode;
  state.leaflet.tileLayerSourceId = "";
  syncMapDemoPanel();
  syncLeafletCaption();
  setStatus(state.basemapError, "error");
}

function syncLeafletOsmLayers(payload) {
  const map = state.leaflet.map;
  if (!map) {
    return;
  }

  removeLeafletLayer("osmWaterLanduseLayer");
  removeLeafletLayer("osmBuildingsLayer");
  removeLeafletLayer("osmRoadsLayer");
  state.leaflet.osmLayersPayload = payload || null;

  const layers = payload?.layers || {};
  if (state.osmLayerVisibility.water_landuse && layers.water_landuse) {
    state.leaflet.osmWaterLanduseLayer = L.geoJSON(layers.water_landuse, {
      style: (feature) => leafletOsmLayerStyle("water_landuse", feature),
      onEachFeature: bindLeafletOsmPopup,
    }).addTo(map);
  }

  if (state.osmLayerVisibility.buildings && layers.buildings) {
    state.leaflet.osmBuildingsLayer = L.geoJSON(layers.buildings, {
      style: (feature) => leafletOsmLayerStyle("buildings", feature),
      onEachFeature: bindLeafletOsmPopup,
    }).addTo(map);
  }

  if (state.osmLayerVisibility.roads && layers.roads) {
    state.leaflet.osmRoadsLayer = L.geoJSON(layers.roads, {
      style: (feature) => leafletOsmLayerStyle("roads", feature),
      onEachFeature: bindLeafletOsmPopup,
    }).addTo(map);
  }
}

function bindLeafletOsmPopup(feature, layer) {
  const properties = feature.properties || {};
  const label = osmLayerLabel(properties.layer || "");
  const name = properties.name || label || "OSM 要素";
  const typeText = properties.highway
    || properties.building
    || properties.natural
    || properties.water
    || properties.waterway
    || properties.landuse
    || properties.leisure
    || properties.geometry_type
    || "";
  layer.bindPopup(`
    <strong>${escapeHtml(name)}</strong><br>
    <span>${escapeHtml(label)}</span><br>
    <span>${escapeHtml(typeText)}</span>
  `);
}

function leafletOsmLayerStyle(layerId, feature) {
  if (layerId === "water_landuse") {
    const properties = feature.properties || {};
    const isWater = properties.natural === "water" || properties.water || properties.waterway;
    return {
      color: isWater ? "#2f7fb8" : "#6f9b58",
      weight: isWater ? 1.2 : 0.9,
      opacity: isWater ? 0.52 : 0.42,
      fillColor: isWater ? "#8bc7e8" : "#b9d9a3",
      fillOpacity: isWater ? 0.24 : 0.2,
    };
  }

  if (layerId === "buildings") {
    return {
      color: "#9a8f7f",
      weight: 0.8,
      opacity: 0.42,
      fillColor: "#d3c9b8",
      fillOpacity: 0.24,
    };
  }

  return {
    color: "#a0a8a0",
    weight: 1.25,
    opacity: 0.36,
    lineCap: "round",
    lineJoin: "round",
  };
}

function syncLeafletBaseLayers(geojson) {
  const map = state.leaflet.map;
  if (!map || state.leaflet.baseGeoJson === geojson) {
    syncLeafletLayerOrder();
    return;
  }

  removeLeafletLayer("edgeLayer");
  removeLeafletLayer("nodeLayer");

  state.leaflet.edgeLayer = L.geoJSON(geojson, {
    filter: (feature) => shouldRenderWhiteRoadEdge(feature),
    style: (feature) => leafletEdgeStyle(feature),
    onEachFeature: bindLeafletFeaturePopup,
  }).addTo(map);

  state.leaflet.nodeLayer = L.geoJSON(geojson, {
    filter: (feature) => shouldRenderWhiteRoadNode(feature),
    pointToLayer: (feature, latlng) => L.circleMarker(latlng, leafletNodeStyle(feature)),
    onEachFeature: bindLeafletFeaturePopup,
  }).addTo(map);

  state.leaflet.baseGeoJson = geojson;
  state.leaflet.fittedSiteId = "";
  fitLeafletToData();
  syncLeafletLayerOrder();
}

function shouldRenderWhiteRoadEdge(feature) {
  if (feature.properties?.kind !== "edge") {
    return false;
  }

  const edgeType = feature.properties?.edge_type || "";
  if (!state.whiteRoadEdgesVisible && (edgeType === "white_road" || edgeType === "poi_access")) {
    return false;
  }
  return true;
}

function shouldRenderWhiteRoadNode(feature) {
  if (feature.properties?.kind !== "node") {
    return false;
  }

  if (!isPathNodeFeature(feature)) {
    return true;
  }
  if (!state.pathNodesVisible) {
    return false;
  }

  const role = feature.properties?.network_role || "";
  if (!role || !Object.prototype.hasOwnProperty.call(state.whiteRoadRoleVisibility, role)) {
    return true;
  }
  return state.whiteRoadRoleVisibility[role] !== false;
}

function bindLeafletFeaturePopup(feature, layer) {
  const properties = feature.properties || {};
  if (properties.kind === "node") {
    const isWaypoint = isPathNodeFeature(feature);
    if (isWaypoint) {
      const roleLabel = whiteRoadRoleLabel(properties.network_role);
      const sourceOsm = properties.source_osm_id || properties.source_osm_ids;
      const sourceHighway = properties.source_highway || properties.source_highways;
      layer.bindPopup(`
        <strong>${escapeHtml(properties.name || "道路接驳点")}</strong><br>
        <span>${escapeHtml(roleLabel)}</span>
        ${leafletDetailRows([
          ["network_role", properties.network_role],
          ["source_osm_id(s)", sourceOsm],
          ["source_highway(s)", sourceHighway],
          ["anchor_for", properties.anchor_for || properties.anchor_for_name],
          ["projection_distance_m", properties.projection_distance_m],
        ])}
        <span>用于检查白线道路骨架，默认不作为搜索目的地展示。</span>
      `);
      layer.on("click", () => {
        state.focusedNodeId = properties.id || "";
        selectResultByNodeId(state.focusedNodeId, {
          focusMap: false,
          openDetail: true,
          scrollIntoView: true,
        });
        syncLeafletRouteLayer();
      });
      return;
    }

    const indoorButton = properties.indoor_supported
      ? `
        <button
          class="ghost-button leaflet-popup-button"
          type="button"
          data-enter-indoor="${escapeHtml(properties.building_id || properties.id || "")}"
          data-indoor-floor="${escapeHtml(properties.default_floor_id || "")}"
        >
          进入室内导航
        </button>
      `
      : "";
    layer.bindPopup(`
      <strong>${escapeHtml(properties.name || properties.id)}</strong><br>
      <span>${escapeHtml(properties.category_label || properties.category || "")}</span><br>
      <button class="route-button leaflet-popup-button" type="button" data-route-target="${escapeHtml(properties.id || "")}">
        从当前起点规划路线
      </button>
      <button class="ghost-button leaflet-popup-button" type="button" data-nearby-center="${escapeHtml(properties.id || "")}">
        查附近设施
      </button>
      ${indoorButton}
    `);
    layer.bindTooltip(escapeHtml(properties.name || properties.id), {
      direction: "top",
      sticky: true,
      opacity: 0.9,
    });
    layer.on("click", () => {
      state.focusedNodeId = properties.id || "";
      selectResultByNodeId(state.focusedNodeId, {
        focusMap: false,
        openDetail: true,
        scrollIntoView: true,
      });
      syncLeafletRouteLayer();
    });
    return;
  }

  if (properties.kind === "edge") {
    const sourceText = edgeGeometrySourceLabel(properties.geometry_source);
    const confidenceText = properties.geometry_confidence
      ? `<br><span>匹配置信度：${escapeHtml(String(properties.geometry_confidence))}</span>`
      : "";
    layer.bindPopup(`
      <strong>${escapeHtml(properties.name || "道路")}</strong><br>
      <span>${escapeHtml(properties.edge_type || "")}</span><br>
      <span>${escapeHtml(sourceText)}</span>${confidenceText}
      ${leafletDetailRows([
        ["from", properties.from],
        ["to", properties.to],
        ["distance_m", properties.distance_m],
        ["geometry_source", properties.geometry_source],
        ["source_osm_id", properties.source_osm_id],
        ["source_highway", properties.source_highway],
      ])}
    `);
  }
}

function leafletDetailRows(rows) {
  return rows
    .map(([label, value]) => {
      const text = formatLeafletDetailValue(value);
      return text ? `<br><span>${escapeHtml(label)}：${escapeHtml(text)}</span>` : "";
    })
    .join("");
}

function formatLeafletDetailValue(value) {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return String(value);
}

function leafletEdgeStyle(feature) {
  const edgeType = feature.properties?.edge_type || "";
  const isRoad = edgeType.includes("road");
  const geometrySource = feature.properties?.geometry_source || "";
  const isOsmMatched = geometrySource === "osm_matched";
  const isManual = geometrySource === "manual";
  const isFallback = Boolean(feature.properties?.is_fallback_geometry);
  return {
    color: isOsmMatched ? "#2f7f6f" : isRoad ? "#6f7f78" : "#8b9a94",
    weight: isOsmMatched ? 3.4 : isRoad ? 3 : 2.4,
    opacity: isFallback ? 0.34 : isOsmMatched ? 0.58 : isManual ? 0.46 : 0.42,
    dashArray: isFallback ? "5 7" : "",
    lineCap: "round",
    lineJoin: "round",
  };
}

function edgeGeometrySourceLabel(source) {
  if (source === "osm_matched") {
    return "OSM 匹配线形";
  }
  if (source === "manual") {
    return "手工校准线形";
  }
  if (source === "fallback_line") {
    return "fallback 直线段";
  }
  return source ? `线形来源：${source}` : "线形来源：未知";
}

function whiteRoadRoleLabel(role) {
  if (role === "junction") {
    return "白线道路交叉口";
  }
  if (role === "bend") {
    return "白线道路硬拐点";
  }
  if (role === "endpoint") {
    return "白线道路端点";
  }
  if (role === "poi_access") {
    return "POI 道路接驳点";
  }
  return "道路接驳点";
}

function leafletNodeStyle(feature) {
  const category = feature.properties?.category || "";
  const networkRole = feature.properties?.network_role || "";
  const isHighlighted = getMapHighlightNodeIds().has(feature.properties?.id || "");
  const isWaypoint = isPathNodeFeature(feature);
  const roleFillColor = {
    junction: "#0f766e",
    bend: "#2563eb",
    endpoint: "#64748b",
    poi_access: "#d98214",
  }[networkRole];
  const waypointRadius = networkRole === "poi_access" ? 4.8 : networkRole === "junction" ? 3.2 : 2.5;
  return {
    radius: isHighlighted ? 9 : isWaypoint ? waypointRadius : 5.8,
    color: "#ffffff",
    weight: isHighlighted ? 3 : isWaypoint ? 1 : 1.5,
    fillColor: roleFillColor || colorForCategory(category),
    opacity: isWaypoint && !isHighlighted ? 0.72 : 1,
    fillOpacity: isHighlighted ? 0.96 : isWaypoint ? 0.5 : 0.8,
  };
}

function syncLeafletRouteLayer() {
  const map = state.leaflet.map;
  if (!map) {
    return;
  }

  removeLeafletLayer("routeLayer");
  const layer = L.layerGroup().addTo(map);
  const nodeIndex = mapNodeIndex();
  let renderedRouteGeoJson = false;
  const routeGeoJson = state.currentRoute?.ui?.route_geojson || state.currentRoute?.ui?.geojson;

  if (isRenderableRouteGeoJson(routeGeoJson)) {
    try {
      addLeafletRouteGeoJson(layer, routeGeoJson, {
        color: "#ffffff",
        weight: 16,
        opacity: 0.82,
        lineCap: "round",
        lineJoin: "round",
      });
      addLeafletRouteGeoJson(layer, routeGeoJson, {
        color: "#8f3c12",
        weight: 11,
        opacity: 0.58,
        lineCap: "round",
        lineJoin: "round",
      });
      addLeafletRouteGeoJson(layer, routeGeoJson, {
        color: "#f59e0b",
        weight: 6,
        opacity: 0.96,
        lineCap: "round",
        lineJoin: "round",
      });
      renderedRouteGeoJson = true;
    } catch (error) {
      console.warn("Leaflet route GeoJSON render failed, falling back to node path.", error);
    }
  }

  if (!renderedRouteGeoJson) {
    const routePath = state.currentRoute?.ui?.mappable_path_node_ids || [];
    const routeLatLngs = routePath
      .map((nodeId) => nodeIndex.get(nodeId))
      .filter(Boolean)
      .map((node) => [node.lat, node.lng]);

    if (routeLatLngs.length >= 2) {
      L.polyline(routeLatLngs, {
        color: "#ffffff",
        weight: 16,
        opacity: 0.82,
        lineCap: "round",
        lineJoin: "round",
      }).addTo(layer);
      L.polyline(routeLatLngs, {
        color: "#8f3c12",
        weight: 11,
        opacity: 0.54,
        lineCap: "round",
        lineJoin: "round",
      }).addTo(layer);
      L.polyline(routeLatLngs, {
        color: "#f59e0b",
        weight: 6,
        opacity: 0.94,
        lineCap: "round",
        lineJoin: "round",
      }).addTo(layer);
    }
  }

  getMapHighlightNodeIds().forEach((nodeId) => {
    const node = nodeIndex.get(nodeId);
    if (!node) {
      return;
    }
    if (!state.pathNodesVisible && isPathNodeData(node)) {
      return;
    }
    L.circleMarker([node.lat, node.lng], {
      radius: 10,
      color: "#ffffff",
      weight: 3,
      fillColor: "#d98214",
      fillOpacity: 0.9,
    })
      .bindTooltip(node.name, { direction: "top" })
      .addTo(layer);
  });

  state.leaflet.routeLayer = layer;
  syncLeafletLayerOrder();
}

function syncLeafletLayerOrder() {
  const order = [
    state.leaflet.tileLayer,
    state.leaflet.osmWaterLanduseLayer,
    state.leaflet.osmBuildingsLayer,
    state.leaflet.osmRoadsLayer,
    state.leaflet.edgeLayer,
    state.leaflet.nodeLayer,
    state.leaflet.routeLayer,
  ];

  order.forEach((layer, index) => {
    if (!layer) {
      return;
    }
    if (index === 0 && typeof layer.bringToBack === "function") {
      layer.bringToBack();
      return;
    }
    if (typeof layer.bringToFront === "function") {
      layer.bringToFront();
    }
  });
}

function addLeafletRouteGeoJson(layer, routeGeoJson, style) {
  L.geoJSON(routeGeoJson, {
    filter: (feature) => isRouteLineGeometry(feature?.geometry || feature),
    style: () => style,
  }).addTo(layer);
}

function isRenderableRouteGeoJson(routeGeoJson) {
  if (!routeGeoJson || typeof routeGeoJson !== "object") {
    return false;
  }

  if (routeGeoJson.type === "FeatureCollection") {
    return Array.isArray(routeGeoJson.features)
      && routeGeoJson.features.some((feature) => isRouteLineGeometry(feature?.geometry));
  }

  if (routeGeoJson.type === "Feature") {
    return isRouteLineGeometry(routeGeoJson.geometry);
  }

  return isRouteLineGeometry(routeGeoJson);
}

function isRouteLineGeometry(geometry) {
  return geometry?.type === "LineString" || geometry?.type === "MultiLineString";
}

function fallbackToSvgMap(error) {
  const message = `Leaflet 地图加载失败，已回退 SVG 简图：${error.message || error}。`;
  state.mapRenderer = "simple_svg";
  state.mapRenderToken += 1;
  renderSvgMap(message, state.mapRenderToken);
  setStatus(message, "error");
}

function setMapRendererVisibility(renderer) {
  const stage = document.querySelector(".map-stage");
  const svg = document.querySelector("#campus-map");
  const leaflet = document.querySelector("#leaflet-map");
  const indoor = document.querySelector("#indoor-map-view");
  const mapViewMode = selectedMapViewMode();

  if (stage) {
    stage.classList.toggle("map-renderer-simple-svg", renderer === "simple_svg");
    stage.classList.toggle("map-renderer-leaflet", renderer === "leaflet_geo");
    stage.classList.toggle("map-view-outdoor", mapViewMode === "outdoor");
    stage.classList.toggle("map-view-indoor", mapViewMode === "indoor");
    stage.dataset.renderer = renderer;
    stage.dataset.mapView = mapViewMode;
  }
  if (svg) {
    const showSvg = mapViewMode === "outdoor" && renderer === "simple_svg";
    svg.hidden = !showSvg;
    svg.style.display = showSvg ? "block" : "none";
    svg.setAttribute("aria-hidden", String(!showSvg));
  }
  if (leaflet) {
    const showLeaflet = mapViewMode === "outdoor" && renderer === "leaflet_geo";
    leaflet.hidden = !showLeaflet;
    leaflet.style.display = showLeaflet ? "block" : "none";
    leaflet.setAttribute("aria-hidden", String(!showLeaflet));
  }
  if (indoor) {
    const showIndoor = mapViewMode === "indoor";
    indoor.hidden = !showIndoor;
    indoor.style.display = showIndoor ? "grid" : "none";
    indoor.setAttribute("aria-hidden", String(!showIndoor));
  }
  syncMapViewToggle();
}

function syncMapDemoPanel() {
  const renderer = selectedMapRenderer();
  const rendererLabel = renderer === "leaflet_geo" ? "Leaflet 真实地图" : "SVG 稳定简图";

  document.querySelectorAll("[data-map-renderer]").forEach((button) => {
    const isActive = button.dataset.mapRenderer === renderer;
    const isAvailable = availableMapRenderers().includes(button.dataset.mapRenderer || "");
    button.classList.toggle("active", isActive);
    button.disabled = !isAvailable;
    button.setAttribute("aria-pressed", String(isActive));
  });

  const basemapMode = selectedBasemapMode();
  const basemap = basemapConfig(basemapMode);
  document.querySelectorAll("[data-map-basemap]").forEach((button) => {
    const isActive = button.dataset.mapBasemap === basemapMode;
    const isAvailable = availableBasemapModes().some((mode) => mode.id === button.dataset.mapBasemap);
    button.classList.toggle("active", isActive);
    button.disabled = !isAvailable;
    button.setAttribute("aria-pressed", String(isActive));
  });

  document.querySelectorAll("[data-osm-layer]").forEach((button) => {
    const layerId = button.dataset.osmLayer || "";
    const isAvailable = availableOsmLayerConfigs().some((layer) => layer.id === layerId);
    const isActive = Boolean(state.osmLayerVisibility[layerId]);
    button.classList.toggle("active", isActive);
    button.disabled = !isAvailable || renderer !== "leaflet_geo";
    button.setAttribute("aria-pressed", String(isActive));
  });

  document.querySelectorAll("[data-white-road-role]").forEach((button) => {
    const role = button.dataset.whiteRoadRole || "";
    const isActive = state.whiteRoadRoleVisibility[role] !== false;
    button.classList.toggle("active", state.pathNodesVisible && isActive);
    button.disabled = renderer !== "leaflet_geo" || !state.pathNodesVisible;
    button.setAttribute("aria-pressed", String(state.pathNodesVisible && isActive));
  });

  const whiteRoadEdgeToggle = document.querySelector("#white-road-edge-toggle");
  if (whiteRoadEdgeToggle) {
    whiteRoadEdgeToggle.checked = state.whiteRoadEdgesVisible !== false;
    whiteRoadEdgeToggle.disabled = renderer !== "leaflet_geo";
  }

  const pathNodeToggle = document.querySelector("#path-node-toggle");
  if (pathNodeToggle) {
    pathNodeToggle.checked = state.pathNodesVisible;
    pathNodeToggle.disabled = false;
  }

  const rendererStatus = document.querySelector("#map-renderer-status");
  if (rendererStatus) {
    rendererStatus.textContent = rendererLabel;
    rendererStatus.className = `status-pill ${renderer === "leaflet_geo" ? "status-pill-primary" : "status-pill-muted"}`;
  }

  const basemapStatus = document.querySelector("#map-basemap-status");
  if (basemapStatus) {
    const networkLabel = basemap?.network_required ? "联网瓦片" : "本地空白";
    basemapStatus.textContent = state.basemapError
      ? "底图加载异常 · GeoJSON 可用"
      : `底图 ${basemapModeLabel(basemapMode)} · ${networkLabel}`;
    basemapStatus.className = state.basemapError
      ? "status-pill status-error"
      : `status-pill ${basemapMode === "none" ? "status-pill-muted" : "status-pill-primary"}`;
  }

  const osmStatus = document.querySelector("#map-osm-status");
  if (osmStatus) {
    const osmStats = state.osmLayersStats || {};
    if (state.osmLayerError) {
      osmStatus.textContent = `${state.osmLayerError} · 核心地图可用`;
      osmStatus.className = "status-pill status-error";
    } else if (osmStats.feature_count) {
      osmStatus.textContent = `本地 OSM ${osmStats.feature_count} 项 · ${enabledOsmLayerCount()} 层开启`;
      osmStatus.className = "status-pill status-pill-primary";
    } else {
      osmStatus.textContent = "本地 OSM 待加载";
      osmStatus.className = "status-pill status-pill-muted";
    }
  }

  const leafletElement = document.querySelector("#leaflet-map");
  if (leafletElement) {
    leafletElement.classList.toggle("leaflet-basemap-none", basemapMode === "none");
  }

  const mapData = state.bootstrap?.map || {};
  const stats = state.mapGeoJsonStats || {};
  const nodeCount = stats.node_feature_count ?? mapData.node_count ?? 0;
  const poiCount = stats.poi_node_count ?? mapData.poi_node_count ?? 0;
  const waypointCount = stats.waypoint_node_count ?? mapData.waypoint_node_count ?? 0;
  const edgeCount = stats.edge_feature_count ?? mapData.edge_count ?? 0;
  const osmMatchedCount = stats.osm_matched_edge_count ?? mapData.osm_matched_edge_count ?? 0;
  const manualCount = stats.manual_geometry_edge_count ?? mapData.manual_geometry_edge_count ?? 0;
  const fallbackCount = stats.fallback_edge_count ?? mapData.fallback_edge_count ?? 0;
  const coverageRatio = stats.geometry_coverage_ratio ?? mapData.geometry_coverage_ratio ?? 0;
  const dataStatus = document.querySelector("#map-data-status");
  if (dataStatus) {
    const siteName = state.bootstrap?.site?.name || "当前站点";
    dataStatus.textContent = `已载入 ${siteName} 主地图 · ${poiCount || nodeCount} 个地点`;
    dataStatus.title = `路网点 ${waypointCount}，OSM ${osmMatchedCount}，manual ${manualCount}，fallback ${fallbackCount}`;
  }

  const routeStatus = document.querySelector("#map-route-status");
  if (routeStatus) {
    const routeStats = routeGeometryStats();
    if (state.currentRoute && routeStats && routeStats.route_segment_count) {
      const routeOsmCount = Number(routeStats.osm_matched_segment_count) || 0;
      const routeManualCount = Number(routeStats.manual_geometry_segment_count) || 0;
      const routeFallbackCount = Number(routeStats.fallback_segment_count) || 0;
      routeStatus.textContent = mapRouteStatusText(state.currentRoute, routeStats);
      routeStatus.title = `OSM ${routeOsmCount}，manual ${routeManualCount}，fallback ${routeFallbackCount}`;
      routeStatus.className = "status-pill status-pill-strong";
    } else if (state.focusedNodeId) {
      routeStatus.textContent = `定位 ${getNodeName(state.focusedNodeId)}`;
      routeStatus.className = "status-pill status-pill-primary";
    } else {
      routeStatus.textContent = "路线未规划";
      routeStatus.className = "status-pill status-pill-muted";
    }
  }
}

function formatRatioPercent(value) {
  const numeric = Number(value) || 0;
  return `${Math.round(numeric * 1000) / 10}%`;
}

function enabledOsmLayerCount() {
  return availableOsmLayerConfigs().filter((layer) => state.osmLayerVisibility[layer.id]).length;
}

function osmLayerCaptionText() {
  const stats = state.osmLayersStats || {};
  if (state.osmLayerError) {
    return "本地 OSM 图层加载提示已显示，核心项目地图继续可用。";
  }
  if (!stats.feature_count) {
    return "本地 OSM 图层正在准备或尚未加载。";
  }

  const metadata = state.osmLayersMetadata || {};
  const attribution = metadata.license?.attribution || "© OpenStreetMap contributors";
  return `本地 OSM 图层：道路 ${stats.roads_feature_count || 0}、建筑 ${stats.buildings_feature_count || 0}、水域/绿地 ${stats.water_landuse_feature_count || 0}，${attribution}。`;
}

function clearLeafletLayers() {
  if (state.leaflet.map) {
    state.leaflet.map.closePopup();
  }
  removeLeafletLayer("tileLayer");
  removeLeafletLayer("osmWaterLanduseLayer");
  removeLeafletLayer("osmBuildingsLayer");
  removeLeafletLayer("osmRoadsLayer");
  removeLeafletLayer("edgeLayer");
  removeLeafletLayer("nodeLayer");
  removeLeafletLayer("routeLayer");
  state.leaflet.tileLayerMode = "";
  state.leaflet.tileLayerSourceId = "";
  state.leaflet.osmLayersPayload = null;
  state.leaflet.baseGeoJson = null;
  state.leaflet.fittedSiteId = "";
  state.leaflet.siteBoundsFitted = false;
}

function mapRouteStatusText(route, routeStats) {
  const geometryText = `${routeStats.geometry_segment_count}/${routeStats.route_segment_count} 段真实线形`;
  if (route.route_type === "multi_target") {
    const summary = route.summary || {};
    return `已规划多目标 · ${summary.target_count || 0} 个目标 · ${geometryText}`;
  }

  return `已规划：${route.start_node_name} -> ${route.target_node_name} · ${geometryText}`;
}

function removeLeafletLayer(layerName) {
  const map = state.leaflet.map;
  const layer = state.leaflet[layerName];
  if (map && layer) {
    map.removeLayer(layer);
  }
  state.leaflet[layerName] = null;
}

function fitLeafletToData() {
  const map = state.leaflet.map;
  if (!map) {
    return;
  }

  const layers = [state.leaflet.edgeLayer, state.leaflet.nodeLayer].filter(Boolean);
  if (!layers.length) {
    fitLeafletToSiteBounds();
    return;
  }

  const bounds = L.featureGroup(layers).getBounds();
  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.18), { animate: false });
    state.leaflet.fittedSiteId = currentSiteId();
  }
}

function fitLeafletToSiteBounds() {
  const map = state.leaflet.map;
  if (!map || !window.L) {
    return;
  }

  const bounds = leafletSiteBounds();
  if (bounds && bounds.isValid()) {
    map.fitBounds(bounds.pad(0.08), {
      animate: false,
      maxZoom: 17,
    });
    state.leaflet.siteBoundsFitted = true;
    return;
  }

  map.setView(mapCenterLatLng(), 17, { animate: false });
  state.leaflet.siteBoundsFitted = true;
}

function invalidateLeafletSize() {
  const map = state.leaflet.map;
  if (!map) {
    return;
  }
  setTimeout(() => {
    map.invalidateSize(false);
    if (!state.leaflet.siteBoundsFitted) {
      fitLeafletToSiteBounds();
    }
    if (state.leaflet.fittedSiteId !== currentSiteId()) {
      fitLeafletToData();
    }
  }, 0);
}

function mapCenterLatLng() {
  const bounds = state.bootstrap?.map?.bounds || {};
  const lat = ((bounds.lat_min || 0) + (bounds.lat_max || 0)) / 2 || 39.9915;
  const lng = ((bounds.lng_min || 0) + (bounds.lng_max || 0)) / 2 || 116.307;
  return [lat, lng];
}

function leafletSiteBounds() {
  const bounds = state.bootstrap?.map?.bounds || {};
  const latMin = Number(bounds.lat_min);
  const latMax = Number(bounds.lat_max);
  const lngMin = Number(bounds.lng_min);
  const lngMax = Number(bounds.lng_max);
  if (![latMin, latMax, lngMin, lngMax].every(Number.isFinite)) {
    return null;
  }

  return L.latLngBounds(
    [latMin, lngMin],
    [latMax, lngMax],
  );
}

function mapNodeIndex() {
  const nodes = state.bootstrap?.map?.nodes || [];
  return new Map(nodes.map((node) => [node.id, node]));
}

function isPathNodeId(nodeId) {
  if (!nodeId) {
    return false;
  }
  const node = mapNodeIndex().get(nodeId);
  return Boolean(node && isPathNodeData(node));
}

function getMapHighlightNodeIds() {
  const highlightNodeIds = new Set();
  if (state.focusedNodeId) {
    highlightNodeIds.add(state.focusedNodeId);
  }
  if (state.currentRoute) {
    (state.currentRoute.ui?.highlight_node_ids || []).forEach((item) => {
      if (item) {
        highlightNodeIds.add(item);
      }
    });
  }
  return highlightNodeIds;
}

function projectNode(node, bounds) {
  const latRange = Math.max(bounds.lat_max - bounds.lat_min, 0.0001);
  const lngRange = Math.max(bounds.lng_max - bounds.lng_min, 0.0001);
  const x =
    MAP_PADDING +
    ((node.lng - bounds.lng_min) / lngRange) * (MAP_WIDTH - MAP_PADDING * 2);
  const y =
    MAP_HEIGHT -
    MAP_PADDING -
    ((node.lat - bounds.lat_min) / latRange) * (MAP_HEIGHT - MAP_PADDING * 2);
  return { x, y };
}

function transformMapPoint(point) {
  return {
    x: point.x * state.mapView.scale + state.mapView.translateX,
    y: point.y * state.mapView.scale + state.mapView.translateY,
  };
}

function estimateLabelWidth(value) {
  const textLength = String(value ?? "").length;
  return clamp(textLength * 14 + 18, 42, 150);
}

function colorForCategory(category) {
  const palette = {
    entrance: "#b55e3b",
    education: "#1f5f8b",
    landmark: "#8f7131",
    dormitory: "#6d5f9f",
    catering: "#2f6b5f",
    shopping: "#7a5a40",
    restroom: "#b4862f",
    sports: "#9b4a4a",
    parking: "#606c86",
    road: "#94a3ab",
  };
  return palette[category] || "#51606f";
}

function firstMappableNodeId(items) {
  if (!Array.isArray(items)) {
    return "";
  }

  const mappableItem = items.find((item) => item.has_map_location && resolveResultRouteTargetId(item));
  if (mappableItem) {
    return resolveResultRouteTargetId(mappableItem);
  }

  const fallbackItem = items.find((item) => resolveResultRouteTargetId(item));
  return fallbackItem ? resolveResultRouteTargetId(fallbackItem) : "";
}

function getNodeName(nodeId) {
  if (!state.bootstrap || !nodeId) {
    return "";
  }
  const routeTarget = state.bootstrap.route_targets.find((item) => item.id === nodeId);
  if (routeTarget) {
    return routeTarget.name;
  }
  const startNode = state.bootstrap.start_nodes.find((item) => item.id === nodeId);
  return startNode ? startNode.name : nodeId;
}

function populateSelect(selectElement, options, selectedValue) {
  selectElement.innerHTML = options
    .map(
      (option) => {
        const selected = option.value === selectedValue ? " selected" : "";
        const disabled = option.disabled ? " disabled" : "";
        return `<option value="${escapeHtml(option.value)}"${selected}${disabled}>${escapeHtml(option.label)}</option>`;
      },
    )
    .join("");
}

function setStatus(message, kind = "info") {
  const banner = document.querySelector("#status-banner");
  banner.className = `status-banner status-${kind}`;
  banner.textContent = message;
}

function feedback(key, fallback) {
  if (!state.bootstrap || !state.bootstrap.feedback_messages) {
    return fallback;
  }
  return state.bootstrap.feedback_messages[key] || fallback;
}

function currentSiteId() {
  return state.bootstrap && state.bootstrap.site ? state.bootstrap.site.id : "";
}

function formatDistance(distanceValue, distanceStatus) {
  if (distanceValue === undefined || distanceValue === null) {
    if (!distanceStatus || distanceStatus === "available" || distanceStatus === "not_requested") {
      return "";
    }
    const statusMap = {
      missing_node_id: "缺少图节点映射",
      unreachable: "路径不可达",
      distance_provider_missing: "未接入距离接口",
      distance_error: "距离计算异常",
    };
    return statusMap[distanceStatus] || "距离未知";
  }
  return `${Number(distanceValue).toFixed(1)} m`;
}

function formatSeconds(seconds) {
  if (seconds === undefined || seconds === null) {
    return "时间未知";
  }
  const totalSeconds = Math.round(Number(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  if (minutes <= 0) {
    return `${remainingSeconds} 秒`;
  }
  return `${minutes} 分 ${remainingSeconds} 秒`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function stripHtml(value) {
  return String(value ?? "").replace(/<[^>]*>/g, "");
}

function clamp(value, minValue, maxValue) {
  return Math.min(Math.max(value, minValue), maxValue);
}

async function apiGet(url) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });
  return handleApiResponse(response);
}

async function apiPost(url, payload) {
  const body = { ...payload };
  if (currentSiteId() && !body.site_id) {
    body.site_id = currentSiteId();
  }

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });
  return handleApiResponse(response);
}

async function handleApiResponse(response) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || `HTTP ${response.status}`);
  }
  return data;
}
