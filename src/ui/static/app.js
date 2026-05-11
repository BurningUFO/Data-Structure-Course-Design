const MAP_WIDTH = 1000;
const MAP_HEIGHT = 720;
const MAP_PADDING = 88;
const MAP_MIN_SCALE = 0.75;
const MAP_MAX_SCALE = 4;
const MAP_ZOOM_STEP = 0.0016;

const state = {
  bootstrap: null,
  activePage: "home",
  activeTab: "scenic",
  expandedPanel: "",
  expandedPanelElement: null,
  expandedPanelPlaceholder: null,
  currentStartNodeId: "",
  focusedNodeId: "",
  currentResults: [],
  currentRoute: null,
  selectedDiaryId: "",
  mapRenderer: "simple_svg",
  mapGeoJson: null,
  mapGeoJsonStats: null,
  mapGeoJsonSiteId: "",
  mapGeoJsonLoading: null,
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
    baseGeoJson: null,
    routeLayer: null,
    fittedSiteId: "",
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
    setStatus(
      `系统就绪，默认起点为 ${getNodeName(state.currentStartNodeId)}。`,
      "success",
    );
  } catch (error) {
    setStatus(`初始化失败：${error.message}`, "error");
  }
}

async function loadSiteBootstrap(siteId) {
  const query = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  const bootstrap = await apiGet(`/api/bootstrap${query}`);
  state.bootstrap = bootstrap;
  state.mapRenderer = bootstrap.map_renderer || bootstrap.map_capabilities?.default_renderer || "simple_svg";
  state.mapGeoJson = null;
  state.mapGeoJsonStats = null;
  state.mapGeoJsonSiteId = "";
  state.mapGeoJsonLoading = null;
  clearLeafletLayers();
  state.currentStartNodeId = bootstrap.default_start_node;
  hydrateBootstrap(bootstrap);
  resetInteractionState({ clearForms: true });
  renderMap();
  return bootstrap;
}

function bindPageShell() {
  document.addEventListener("click", (event) => {
    const pageButton = event.target.closest("[data-page]");
    if (!pageButton) {
      return;
    }

    switchPage(pageButton.dataset.page);
  });

  const sidebarToggle = document.querySelector("#sidebar-toggle");
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      const layout = document.querySelector("#app-layout");
      const isCollapsed = layout.classList.toggle("sidebar-collapsed");
      sidebarToggle.setAttribute("aria-expanded", String(!isCollapsed));
      sidebarToggle.querySelector(".collapse-icon").textContent = isCollapsed ? "›" : "‹";
      const label = sidebarToggle.querySelector(".side-label");
      if (label) {
        label.textContent = isCollapsed ? "展开侧边栏" : "收起侧边栏";
      }
    });
  }

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
    renderMap();
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
    renderMap();
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
    renderMap();
  }
}

function syncExpandButtons(panelName, isExpanded) {
  document.querySelectorAll(`[data-expand-panel="${panelName}"]`).forEach((button) => {
    button.textContent = isExpanded ? "还原" : "放大";
    button.setAttribute("aria-label", isExpanded ? "还原面板" : "放大面板");
    button.classList.toggle("active", isExpanded);
  });
}

function bindTabSwitching() {
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (!button) {
      return;
    }

    switchTab(button.dataset.tab);
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
    });
  });

  document.querySelector("#place-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runQuery("/api/search/places", {
      keyword: document.querySelector("#place-keyword").value.trim(),
      category: document.querySelector("#place-category").value,
      sort_field: document.querySelector("#place-sort").value,
      start_node_id: state.currentStartNodeId,
      limit: 6,
    });
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

  document.querySelector("#aigc-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await runAigcPreview();
  });

  document.querySelector("#aigc-sample").addEventListener("change", (event) => {
    fillAigcFormFromSample(event.target.value);
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
    setStatus(
      `当前起点已切换为 ${getNodeName(state.currentStartNodeId)}。`,
      "info",
    );
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
      switchTab("scenic");
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

  document.querySelector("#results-list").addEventListener("click", async (event) => {
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

    const routeButton = event.target.closest("[data-route-target]");
    if (routeButton) {
      await planRoute(routeButton.dataset.routeTarget);
    }
  });
}

function bindMapInteractions() {
  const svg = document.querySelector("#campus-map");
  const resetButton = document.querySelector("#map-reset-view");
  if (!svg) {
    return;
  }

  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    zoomMapAt(event.offsetX, event.offsetY, event.deltaY);
  }, { passive: false });

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
      resetMapView();
      setStatus("校园简图已还原到原始比例。", "info");
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
  resetMapViewState();
  if (selectedMapRenderer() === "leaflet_geo") {
    fitLeafletToData();
  }
  renderMap();
}

function resetMapViewState() {
  state.mapView.scale = 1;
  state.mapView.translateX = 0;
  state.mapView.translateY = 0;
  state.mapView.isPanning = false;
}

function switchTab(tab) {
  if (!tab) {
    return;
  }

  switchPage("app");
  state.activeTab = tab;

  document.querySelectorAll("[data-tab]").forEach((item) => {
    item.classList.toggle("active", item.dataset.tab === tab);
  });

  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tab);
  });

  updateActiveFeatureCaption();

  if (tab === "help") {
    setStatus("已打开帮助说明，可按推荐链路完成系统演示。", "info");
  }
}

function resetInteractionState(options = {}) {
  state.currentResults = [];
  state.currentRoute = null;
  state.focusedNodeId = "";
  state.currentStartNodeId = state.bootstrap ? state.bootstrap.default_start_node : "";
  state.selectedDiaryId = "";
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
  renderMap();
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
  setSelectValue("#scenic-sort", "heat");
  setSelectValue("#place-sort", "distance_m");
  setSelectValue("#catering-sort", "distance_m");
  setSelectValue("#route-target", "library");
  setMultipleSelectValues("#multi-route-targets", []);
  setSelectValue("#route-strategy", "shortest_distance");
  setSelectValue("#route-transport", "any");
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

function hydrateBootstrap(bootstrap) {
  document.querySelector("#product-title").textContent = bootstrap.product.name;
  document.querySelector("#product-stage").textContent = bootstrap.product.stage;
  document.querySelector("#hero-title").textContent = `${bootstrap.site.name} 导览演示台`;
  document.querySelector("#hero-description").textContent = [
    bootstrap.site.description,
    bootstrap.site.location ? `地点：${bootstrap.site.location}` : "",
    "当前页面覆盖首页、站点、导航、帮助和核心功能入口。",
  ]
    .filter(Boolean)
    .join(" ");

  document.querySelector("#stat-map-nodes").textContent = String(bootstrap.map.node_count);
  document.querySelector("#stat-route-targets").textContent = String(
    bootstrap.stats.route_target_count,
  );
  document.querySelector("#stat-diaries").textContent = String(bootstrap.stats.diary_count);

  populateSelect(
    document.querySelector("#site-selector"),
    bootstrap.sites.map((item) => ({
      value: item.id,
      label: `${item.name} · ${item.location || item.id}`,
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
    document.querySelector("#route-target"),
    bootstrap.route_targets.map((item) => ({
      value: item.id,
      label: `${item.name} · ${item.category_label} · ${item.graph_type}`,
    })),
    "library",
  );

  populateSelect(
    document.querySelector("#multi-route-targets"),
    bootstrap.route_targets.map((item) => ({
      value: item.id,
      label: `${item.name} · ${item.category_label} · ${item.graph_type}`,
    })),
    "",
  );

  const diaryDestinationOptions = [{ value: "", label: "不绑定路线目标" }].concat(
    bootstrap.route_targets.map((item) => ({
      value: item.id,
      label: `${item.name} · ${item.category_label} · ${item.graph_type}`,
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
    "any",
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

  const sortOptions = bootstrap.controls.sort_options.map((item) => ({
    value: item.value,
    label: item.label,
  }));
  populateSelect(document.querySelector("#scenic-sort"), sortOptions, "heat");
  populateSelect(document.querySelector("#place-sort"), sortOptions, "distance_m");
  populateSelect(document.querySelector("#catering-sort"), sortOptions, "distance_m");

  renderPresetButtons("#scenic-presets", bootstrap.presets.scenic, handleScenicPreset);
  renderPresetButtons("#place-presets", bootstrap.presets.place, handlePlacePreset);
  renderPresetButtons("#catering-presets", bootstrap.presets.catering, handleCateringPreset);
  renderPresetButtons("#diary-presets", bootstrap.presets.diary, handleDiaryPreset);
  renderPresetButtons("#aigc-presets", bootstrap.presets.aigc, handleAigcPreset);
  renderPresetButtons("#route-presets", bootstrap.presets.route, handleRoutePreset);
  renderPresetButtons("#multi-route-presets", bootstrap.presets.multi_route, handleMultiRoutePreset);
  fillAigcFormFromSample(defaultAigcSampleId());
  renderFeatureGrid(bootstrap.navigation);
  renderHelpPanel(bootstrap.help);
  updateActiveFeatureCaption();
}

function renderFeatureGrid(navigation) {
  const container = document.querySelector("#feature-grid");
  container.innerHTML = navigation
    .map((item) => {
      const statusLabel = item.status === "ready" ? "可使用" : "功能扩展";
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

function renderHelpPanel(help) {
  document.querySelector("#help-stage").textContent = help.stage;
  document.querySelector("#help-launch").textContent =
    `启动：${help.launch_command}，浏览器访问：${help.browser_url}`;
  document.querySelector("#help-flow").innerHTML = help.demo_flow
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  document.querySelector("#help-checks").innerHTML = help.checks
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function updateActiveFeatureCaption() {
  if (!state.bootstrap) {
    return;
  }
  const feature = state.bootstrap.navigation.find((item) => item.id === state.activeTab);
  const caption = document.querySelector("#active-feature-caption");
  if (feature && caption) {
    caption.textContent = feature.description;
  }
}

function renderPresetButtons(containerSelector, presets, onClick) {
  const container = document.querySelector(containerSelector);
  container.innerHTML = "";

  presets.forEach((preset) => {
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
  });
}

function handlePlacePreset(preset) {
  document.querySelector("#place-keyword").value = preset.keyword || "";
  document.querySelector("#place-category").value = preset.category || "";
  void runQuery("/api/search/places", {
    keyword: preset.keyword || "",
    category: preset.category || "",
    sort_field: document.querySelector("#place-sort").value,
    start_node_id: state.currentStartNodeId,
    limit: 6,
  });
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

async function runAigcPreview() {
  setStatus("正在生成 AIGC 轻量预览...", "loading");
  renderRoute(null, "AIGC 预览生成中，路径状态已重置。");

  try {
    const response = await apiPost("/api/aigc/preview", {
      sample_id: document.querySelector("#aigc-sample").value,
      prompt: document.querySelector("#aigc-prompt").value.trim(),
      style: document.querySelector("#aigc-style").value,
      duration_s: document.querySelector("#aigc-duration").value,
    });

    state.currentResults = response.results || response.data || [];
    state.currentRoute = null;
    state.focusedNodeId = "";
    renderResults(response);
    renderRoute(null, "AIGC 预览不产生路径；如需导航，请从查询或日记结果进入路线规划。");
    renderMap();

    if (!response.success) {
      setStatus(response.message || "AIGC 预览生成失败", "error");
      return;
    }

    const preview = state.currentResults[0];
    setStatus(
      `AIGC 轻量预览已生成：${preview.title}。当前为模板化原型，不调用真实模型。`,
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
    renderRoute(null, "AIGC 预览失败，路径状态已重置。");
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
  renderRoute(null, "日记管理操作中，路径状态已重置。");

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
    renderRoute(null, "日记管理操作失败，路径状态已重置。");
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
  if (recordCount !== undefined) {
    document.querySelector("#stat-diaries").textContent = String(recordCount);
  }
}

function handleRoutePreset(preset) {
  document.querySelector("#route-target").value = preset.target_node_id;
  void planRoute(preset.target_node_id);
}

function handleMultiRoutePreset(preset) {
  const targetNodeIds = preset.target_node_ids || [];
  setMultipleSelectValues("#multi-route-targets", targetNodeIds);
  void planMultiRoute(targetNodeIds);
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
  renderRoute(null, "查询执行中，路径状态已重置。");

  try {
    const response = await apiPost(url, payload);
    state.currentResults = response.results || response.data || [];
    state.currentRoute = null;
    state.focusedNodeId = firstMappableNodeId(state.currentResults);
    renderResults(response);
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
    renderRoute(null, "查询失败，路径状态已重置。");
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

  if (!items.length) {
    container.className = "card-list empty-state";
    container.textContent = response.message || "暂无结果";
    meta.textContent = "0 条结果";
    return;
  }

  container.className = "card-list";
  meta.textContent = `${response.total} 条结果 · ${response.query_type}`;
  container.innerHTML = items
    .map((item, index) => renderResultCard(item, index, response.query_type || ""))
    .join("");
}

function renderResultCard(item, index, queryType = "") {
  const title = escapeHtml(item.name || item.title || item.route_target_name || "未命名结果");
  const description = item.snippet
    ? escapeHtml(item.snippet)
    : escapeHtml(item.content || item.text_prompt || item.description || "可从该结果继续规划路线。");
  const distanceText = formatDistance(item.distance_m, item.distance_status);
  const scoreText = item.score !== undefined ? `相关度 ${item.score}` : "";
  const routeTarget = item.route_target_node_id || "";
  const focusNode = item.route_target_node_id || "";
  const isDiary = isDiaryResult(item, queryType);
  const isAigc = isAigcResult(item, queryType);
  const diaryId = item.id || item.diary_id || "";
  const mediaMarkup = renderMediaPlaceholders(item);
  const aigcMarkup = isAigc ? renderAigcPreview(item) : "";

  const metrics = [
    item.category_label ? `<span class="metric-pill">${escapeHtml(item.category_label)}</span>` : "",
    item.destination ? `<span class="metric-pill">目的地 ${escapeHtml(item.destination)}</span>` : "",
    item.heat !== undefined ? `<span class="metric-pill">热度 ${item.heat}</span>` : "",
    item.rating !== undefined ? `<span class="metric-pill">评分 ${Number(item.rating).toFixed(1)}</span>` : "",
    item.created_at ? `<span class="metric-pill">${escapeHtml(item.created_at)}</span>` : "",
    item.style_label ? `<span class="metric-pill">${escapeHtml(item.style_label)}</span>` : "",
    item.duration_s !== undefined ? `<span class="metric-pill">${item.duration_s} 秒</span>` : "",
    item.status ? `<span class="metric-pill">${escapeHtml(item.status)}</span>` : "",
    distanceText ? `<span class="metric-pill">${escapeHtml(distanceText)}</span>` : "",
    scoreText ? `<span class="metric-pill">${escapeHtml(scoreText)}</span>` : "",
  ]
    .filter(Boolean)
    .join("");

  const buttons = [
    focusNode
      ? `<button class="ghost-button" type="button" data-focus-node="${escapeHtml(focusNode)}">地图定位</button>`
      : "",
    routeTarget
      ? `<button class="route-button" type="button" data-route-target="${escapeHtml(routeTarget)}">从当前起点规划路线</button>`
      : "",
    isDiary && queryType !== "diary_delete"
      ? `<button class="ghost-button" type="button" data-diary-edit-id="${escapeHtml(diaryId)}">载入编辑</button>`
      : "",
    isDiary && queryType !== "diary_delete"
      ? `<button class="ghost-button" type="button" data-diary-rate-id="${escapeHtml(diaryId)}">快速评 5 分</button>`
      : "",
    isDiary && queryType !== "diary_delete"
      ? `<button class="danger-button" type="button" data-diary-delete-id="${escapeHtml(diaryId)}">删除日记</button>`
      : "",
    isDiary && queryType === "diary_delete"
      ? `<span class="deleted-badge">已从内存态移除</span>`
      : "",
  ]
    .filter(Boolean)
    .join("");

  return `
    <article class="result-card" style="animation-delay: ${index * 0.04}s">
      <h4>${title}</h4>
      <div class="card-metrics">${metrics}</div>
      <p>${description}</p>
      ${mediaMarkup}
      ${aigcMarkup}
      <div class="card-actions">${buttons}</div>
    </article>
  `;
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
        .map((media) => `
          <span class="media-chip">
            <span>${escapeHtml(media.kind)}</span>
            <strong>${escapeHtml(media.value)}</strong>
          </span>
        `)
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
  return `
    <div class="aigc-preview-block">
      <p class="prototype-notice">${escapeHtml(item.prototype_notice || "")}</p>
      <div class="storyboard-grid">
        ${frames
          .map((frame) => `
            <article class="storyboard-frame">
              <span>${frame.time_s}s</span>
              <strong>${escapeHtml(frame.title)}</strong>
              <p>${escapeHtml(frame.visual || frame.caption || "")}</p>
            </article>
          `)
          .join("")}
      </div>
      <div class="pipeline-list">
        ${pipeline.map((step) => `<span>${escapeHtml(step)}</span>`).join("")}
      </div>
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
    stepsContainer.textContent = "暂无步骤";
    routeMeta.textContent = "尚未规划路径";
    return;
  }

  if (route.route_type === "multi_target") {
    renderMultiRoute(route, summaryContainer, stepsContainer, routeMeta);
    return;
  }

  const summary = route.summary || {};
  summaryContainer.className = "route-summary";
  summaryContainer.innerHTML = `
    <article class="summary-card">
      <h4>${escapeHtml(route.start_node_name)} -> ${escapeHtml(route.target_node_name)}</h4>
      <div class="summary-grid">
        <span class="metric-pill">${escapeHtml(summary.strategy_text || "")}</span>
        <span class="metric-pill">${escapeHtml(summary.transport_text || "")}</span>
        <span class="metric-pill">${escapeHtml(summary.distance_text || "")}</span>
        <span class="metric-pill">${escapeHtml(summary.time_text || "")}</span>
      </div>
      <p>层级序列：${escapeHtml(summary.layer_text || "outdoor")}</p>
      <p>节点数：${route.route_overview.node_count}，跨层次数：${route.route_overview.cross_layer_step_count}</p>
    </article>
  `;

  const steps = route.path_steps || [];
  routeMeta.textContent = `${steps.length} 步 · ${route.path_node_names.length} 个节点`;
  stepsContainer.className = "step-list";
  stepsContainer.innerHTML = steps
    .map((step, index) => {
      const edgeName = step.edge_name ? ` · ${escapeHtml(step.edge_name)}` : "";
      return `
        <article class="step-card" style="animation-delay: ${index * 0.03}s">
          <h4>第 ${step.step_index} 步${edgeName}</h4>
          <p>${escapeHtml(step.from_node_name)} -> ${escapeHtml(step.to_node_name)}</p>
          <div class="card-metrics">
            <span class="metric-pill">${escapeHtml(step.display_layer || step.to_layer || "")}</span>
            <span class="metric-pill">${formatDistance(step.distance_m, "available")}</span>
            <span class="metric-pill">${formatSeconds(step.estimated_time_s)}</span>
            <span class="metric-pill">${step.transition_kind === "cross_layer" ? "跨层" : "同层"}</span>
          </div>
          <p>${escapeHtml(step.description || "沿当前道路继续前进。")}</p>
        </article>
      `;
    })
    .join("");
}

function renderMultiRoute(route, summaryContainer, stepsContainer, routeMeta) {
  const summary = route.summary || {};
  summaryContainer.className = "route-summary";
  summaryContainer.innerHTML = `
    <article class="summary-card">
      <h4>多目标路径 · ${escapeHtml(summary.return_to_start_text || "")}</h4>
      <div class="summary-grid">
        <span class="metric-pill">${escapeHtml(summary.strategy_text || "")}</span>
        <span class="metric-pill">${escapeHtml(summary.transport_text || "")}</span>
        <span class="metric-pill">${escapeHtml(summary.distance_text || "")}</span>
        <span class="metric-pill">${escapeHtml(summary.time_text || "")}</span>
      </div>
      <p>访问顺序：${escapeHtml(summary.visit_order_text || "")}</p>
      <p>目标数：${summary.target_count || 0}，路径段数：${summary.leg_count || 0}</p>
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

  stepsContainer.innerHTML = `${legMarkup}${stepMarkup}${overflowText}`;
}

function selectedMapRenderer() {
  if (!state.bootstrap) {
    return "simple_svg";
  }

  const capabilities = state.bootstrap.map_capabilities || {};
  const renderers = Array.isArray(capabilities.renderers) ? capabilities.renderers : ["simple_svg"];
  const renderer = state.mapRenderer || state.bootstrap.map_renderer || capabilities.default_renderer || "simple_svg";
  return renderers.includes(renderer) ? renderer : "simple_svg";
}

function renderMap() {
  if (selectedMapRenderer() === "leaflet_geo") {
    void renderLeafletMap();
    return;
  }
  renderSvgMap();
}

function renderSvgMap(fallbackMessage = "") {
  const svg = document.querySelector("#campus-map");
  const caption = document.querySelector("#map-caption");
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

  const nodeMarkup = mapData.nodes
    .map((node) => {
      const projected = screenNodes.get(node.id);
      const fill = colorForCategory(node.category);
      const isHighlighted = highlightNodeIds.has(node.id);
      const radius = isHighlighted ? 12 : node.category === "entrance" ? 9 : 7;
      const labelDy = node.category === "road" ? 0 : 20;
      const labelText = node.category !== "road" ? escapeHtml(node.name) : "";
      const labelWidth = estimateLabelWidth(node.name);
      const labelX = projected.x - labelWidth / 2;
      const labelY = projected.y + labelDy - 14;
      return `
        <g>
          ${isHighlighted ? `<circle class="route-dot" cx="${projected.x}" cy="${projected.y}" r="${radius + 6}" fill="rgba(181, 94, 59, 0.16)" />` : ""}
          <circle cx="${projected.x}" cy="${projected.y}" r="${radius}" fill="${fill}" stroke="white" stroke-width="3" />
          ${
            node.category !== "road"
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
    ? state.currentRoute.ui.caption
    : state.focusedNodeId
      ? `当前定位：${getNodeName(state.focusedNodeId)}。`
      : `当前展示的是室外节点分布；缩放 ${Math.round(state.mapView.scale * 100)}%，可拖动查看细节。`;
  caption.textContent = fallbackMessage ? `${fallbackMessage} ${captionText}` : captionText;
}

async function renderLeafletMap() {
  const caption = document.querySelector("#map-caption");
  if (!state.bootstrap) {
    setMapRendererVisibility("leaflet_geo");
    caption.textContent = "地图尚未加载。";
    return;
  }

  try {
    setMapRendererVisibility("leaflet_geo");
    ensureLeafletMap();
    caption.textContent = "真实地图实验模式正在加载 GeoJSON...";

    const geojson = await loadMapGeoJson();
    if (selectedMapRenderer() !== "leaflet_geo") {
      return;
    }

    syncLeafletBaseLayers(geojson);
    syncLeafletRouteLayer();
    invalidateLeafletSize();

    const stats = state.mapGeoJsonStats || {};
    caption.textContent = state.currentRoute
      ? state.currentRoute.ui.caption
      : state.focusedNodeId
        ? `真实地图实验模式：当前定位 ${getNodeName(state.focusedNodeId)}。`
        : `真实地图实验模式：已加载 ${stats.node_feature_count || 0} 个节点和 ${stats.edge_feature_count || 0} 条道路。`;
  } catch (error) {
    fallbackToSvgMap(error);
  }
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
      attributionControl: false,
      preferCanvas: true,
    }).setView(center, 17);
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
  state.mapGeoJsonLoading = apiGet(url)
    .then((payload) => {
      if (!payload.success || !payload.geojson || payload.geojson.type !== "FeatureCollection") {
        throw new Error(payload.message || "GeoJSON 响应格式无效");
      }
      state.mapGeoJson = payload.geojson;
      state.mapGeoJsonStats = payload.stats || {};
      state.mapGeoJsonSiteId = siteId;
      return payload.geojson;
    })
    .finally(() => {
      state.mapGeoJsonLoading = null;
    });
  return state.mapGeoJsonLoading;
}

function syncLeafletBaseLayers(geojson) {
  const map = state.leaflet.map;
  if (!map || state.leaflet.baseGeoJson === geojson) {
    return;
  }

  removeLeafletLayer("edgeLayer");
  removeLeafletLayer("nodeLayer");

  state.leaflet.edgeLayer = L.geoJSON(geojson, {
    filter: (feature) => feature.properties?.kind === "edge",
    style: (feature) => leafletEdgeStyle(feature),
    onEachFeature: bindLeafletFeaturePopup,
  }).addTo(map);

  state.leaflet.nodeLayer = L.geoJSON(geojson, {
    filter: (feature) => feature.properties?.kind === "node",
    pointToLayer: (feature, latlng) => L.circleMarker(latlng, leafletNodeStyle(feature)),
    onEachFeature: bindLeafletFeaturePopup,
  }).addTo(map);

  state.leaflet.baseGeoJson = geojson;
  state.leaflet.fittedSiteId = "";
  fitLeafletToData();
}

function bindLeafletFeaturePopup(feature, layer) {
  const properties = feature.properties || {};
  if (properties.kind === "node") {
    layer.bindPopup(`
      <strong>${escapeHtml(properties.name || properties.id)}</strong><br>
      <span>${escapeHtml(properties.category_label || properties.category || "")}</span><br>
      <button class="route-button leaflet-popup-button" type="button" data-route-target="${escapeHtml(properties.id || "")}">
        从当前起点规划路线
      </button>
    `);
    layer.on("click", () => {
      state.focusedNodeId = properties.id || "";
      syncLeafletRouteLayer();
    });
    return;
  }

  if (properties.kind === "edge") {
    layer.bindPopup(`
      <strong>${escapeHtml(properties.name || "道路")}</strong><br>
      <span>${escapeHtml(properties.edge_type || "")}</span><br>
      <span>${formatDistance(properties.distance_m, "available")}</span>
    `);
  }
}

function leafletEdgeStyle(feature) {
  const edgeType = feature.properties?.edge_type || "";
  const isRoad = edgeType.includes("road");
  return {
    color: isRoad ? "#586b78" : "#7b8790",
    weight: isRoad ? 4 : 3,
    opacity: 0.68,
    lineCap: "round",
    lineJoin: "round",
  };
}

function leafletNodeStyle(feature) {
  const category = feature.properties?.category || "";
  const isHighlighted = getMapHighlightNodeIds().has(feature.properties?.id || "");
  return {
    radius: isHighlighted ? 9 : category === "road" ? 4 : 6,
    color: "#ffffff",
    weight: 2,
    fillColor: colorForCategory(category),
    fillOpacity: isHighlighted ? 0.96 : 0.82,
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
        color: "#8f3c12",
        weight: 12,
        opacity: 0.36,
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
        color: "#8f3c12",
        weight: 12,
        opacity: 0.32,
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
  renderSvgMap(message);
  setStatus(message, "error");
}

function setMapRendererVisibility(renderer) {
  const stage = document.querySelector(".map-stage");
  const svg = document.querySelector("#campus-map");
  const leaflet = document.querySelector("#leaflet-map");

  if (stage) {
    stage.classList.toggle("map-renderer-simple-svg", renderer === "simple_svg");
    stage.classList.toggle("map-renderer-leaflet", renderer === "leaflet_geo");
  }
  if (svg) {
    svg.hidden = renderer !== "simple_svg";
  }
  if (leaflet) {
    leaflet.hidden = renderer !== "leaflet_geo";
  }
}

function clearLeafletLayers() {
  removeLeafletLayer("edgeLayer");
  removeLeafletLayer("nodeLayer");
  removeLeafletLayer("routeLayer");
  state.leaflet.baseGeoJson = null;
  state.leaflet.fittedSiteId = "";
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
    map.setView(mapCenterLatLng(), 17);
    return;
  }

  const bounds = L.featureGroup(layers).getBounds();
  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.18), { animate: false });
    state.leaflet.fittedSiteId = currentSiteId();
  }
}

function invalidateLeafletSize() {
  const map = state.leaflet.map;
  if (!map) {
    return;
  }
  setTimeout(() => {
    map.invalidateSize(false);
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

function mapNodeIndex() {
  const nodes = state.bootstrap?.map?.nodes || [];
  return new Map(nodes.map((node) => [node.id, node]));
}

function getMapHighlightNodeIds() {
  const routePath = state.currentRoute?.ui?.mappable_path_node_ids || [];
  const highlightNodeIds = new Set(routePath);
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
  return (
    items.find((item) => item.has_map_location && item.route_target_node_id)?.route_target_node_id ||
    items.find((item) => item.route_target_node_id)?.route_target_node_id ||
    ""
  );
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
      (option) =>
        `<option value="${escapeHtml(option.value)}"${option.value === selectedValue ? " selected" : ""}>${escapeHtml(option.label)}</option>`,
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

