const MAP_WIDTH = 1000;
const MAP_HEIGHT = 720;
const MAP_PADDING = 88;

const state = {
  bootstrap: null,
  activeTab: "scenic",
  currentStartNodeId: "",
  focusedNodeId: "",
  currentResults: [],
  currentRoute: null,
};

document.addEventListener("DOMContentLoaded", () => {
  void init();
});

async function init() {
  bindTabSwitching();
  bindForms();

  try {
    const bootstrap = await apiGet("/api/bootstrap");
    state.bootstrap = bootstrap;
    state.currentStartNodeId = bootstrap.default_start_node;
    hydrateBootstrap(bootstrap);
    renderMap();
    setStatus(
      `演示就绪，默认起点为 ${getNodeName(state.currentStartNodeId)}。`,
      "success",
    );
  } catch (error) {
    setStatus(`初始化失败：${error.message}`, "error");
  }
}

function bindTabSwitching() {
  document.querySelector("#tab-list").addEventListener("click", (event) => {
    const button = event.target.closest(".tab-button");
    if (!button) {
      return;
    }

    const tab = button.dataset.tab;
    state.activeTab = tab;

    document.querySelectorAll(".tab-button").forEach((item) => {
      item.classList.toggle("active", item === button);
    });

    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.panel === tab);
    });
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

  document.querySelector("#route-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const targetNodeId = document.querySelector("#route-target").value;
    await planRoute(targetNodeId);
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

  document.querySelector("#results-list").addEventListener("click", async (event) => {
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

function hydrateBootstrap(bootstrap) {
  document.querySelector("#hero-title").textContent = `${bootstrap.site.name} 导览演示台`;
  document.querySelector("#hero-description").textContent = [
    bootstrap.site.description,
    bootstrap.site.location ? `地点：${bootstrap.site.location}` : "",
    "当前页面覆盖综合查询、场所查询、美食推荐、全文检索与单目标路径规划。",
  ]
    .filter(Boolean)
    .join(" ");

  document.querySelector("#stat-map-nodes").textContent = String(bootstrap.map.node_count);
  document.querySelector("#stat-route-targets").textContent = String(
    bootstrap.stats.route_target_count,
  );
  document.querySelector("#stat-diaries").textContent = String(bootstrap.stats.diary_count);

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
  renderPresetButtons("#route-presets", bootstrap.presets.route, handleRoutePreset);
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

function handleRoutePreset(preset) {
  document.querySelector("#route-target").value = preset.target_node_id;
  void planRoute(preset.target_node_id);
}

async function runQuery(url, payload) {
  setStatus("正在查询，请稍候...", "info");

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
      setStatus("查询成功，但当前没有命中结果。", "info");
      return;
    }

    const routeableCount = response.ui ? response.ui.routeable_result_count : 0;
    setStatus(
      `查询成功，共返回 ${response.total} 条结果，其中 ${routeableCount} 条可直接规划路线。`,
      "success",
    );
  } catch (error) {
    setStatus(`查询失败：${error.message}`, "error");
  }
}

async function planRoute(targetNodeId) {
  if (!targetNodeId) {
    setStatus("当前结果缺少可规划的目标点。", "error");
    return;
  }

  setStatus("正在规划路径，请稍候...", "info");

  try {
    const response = await apiPost("/api/route", {
      start_node_id: state.currentStartNodeId,
      target_node_id: targetNodeId,
      strategy: document.querySelector("#route-strategy").value,
      transport_mode: document.querySelector("#route-transport").value,
    });

    if (!response.success) {
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
    setStatus(`路径规划失败：${error.message}`, "error");
  }
}

function clearRoute() {
  state.currentRoute = null;
  renderRoute(null);
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
    .map((item, index) => renderResultCard(item, index))
    .join("");
}

function renderResultCard(item, index) {
  const title = escapeHtml(item.name || item.title || item.route_target_name || "未命名结果");
  const description = item.snippet
    ? escapeHtml(item.snippet)
    : escapeHtml(item.description || "可从该结果继续规划路线。");
  const distanceText = formatDistance(item.distance_m, item.distance_status);
  const scoreText = item.score !== undefined ? `相关度 ${item.score}` : "";
  const routeTarget = item.route_target_node_id || "";
  const focusNode = item.route_target_node_id || "";

  const metrics = [
    item.category_label ? `<span class="metric-pill">${escapeHtml(item.category_label)}</span>` : "",
    item.heat !== undefined ? `<span class="metric-pill">热度 ${item.heat}</span>` : "",
    item.rating !== undefined ? `<span class="metric-pill">评分 ${Number(item.rating).toFixed(1)}</span>` : "",
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
  ]
    .filter(Boolean)
    .join("");

  return `
    <article class="result-card" style="animation-delay: ${index * 0.04}s">
      <h4>${title}</h4>
      <div class="card-metrics">${metrics}</div>
      <p>${description}</p>
      <div class="card-actions">${buttons}</div>
    </article>
  `;
}

function renderRoute(route) {
  const summaryContainer = document.querySelector("#route-summary");
  const stepsContainer = document.querySelector("#route-steps");
  const routeMeta = document.querySelector("#route-meta");

  if (!route) {
    summaryContainer.className = "route-summary empty-state";
    summaryContainer.textContent = "暂无路径";
    stepsContainer.className = "step-list empty-state";
    stepsContainer.textContent = "暂无步骤";
    routeMeta.textContent = "尚未规划路径";
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

function renderMap() {
  const svg = document.querySelector("#campus-map");
  const caption = document.querySelector("#map-caption");

  if (!state.bootstrap) {
    svg.innerHTML = "";
    caption.textContent = "地图尚未加载。";
    return;
  }

  const mapData = state.bootstrap.map;
  const routePath = state.currentRoute ? state.currentRoute.ui.mappable_path_node_ids : [];
  const highlightNodeIds = new Set(routePath);
  if (state.focusedNodeId) {
    highlightNodeIds.add(state.focusedNodeId);
  }
  if (state.currentRoute) {
    (state.currentRoute.ui.highlight_node_ids || []).forEach((item) => {
      if (item) {
        highlightNodeIds.add(item);
      }
    });
  }

  const projectedNodes = new Map(
    mapData.nodes.map((node) => [node.id, projectNode(node, mapData.bounds)]),
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
      const projected = projectedNodes.get(node.id);
      const fill = colorForCategory(node.category);
      const isHighlighted = highlightNodeIds.has(node.id);
      const radius = isHighlighted ? 13 : node.category === "entrance" ? 10 : 8;
      const labelDy = node.category === "road" ? 26 : 22;
      return `
        <g>
          ${isHighlighted ? `<circle class="route-dot" cx="${projected.x}" cy="${projected.y}" r="${radius + 6}" fill="rgba(181, 94, 59, 0.16)" />` : ""}
          <circle cx="${projected.x}" cy="${projected.y}" r="${radius}" fill="${fill}" stroke="white" stroke-width="3" />
          ${
            node.category !== "road"
              ? `<text class="node-label" x="${projected.x}" y="${projected.y + labelDy}" text-anchor="middle">${escapeHtml(node.name)}</text>`
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
        高亮橙线为当前路径；灰线为可通行道路
      </text>
    </g>
  `;

  svg.innerHTML = `
    <rect x="0" y="0" width="${MAP_WIDTH}" height="${MAP_HEIGHT}" fill="transparent" />
    ${legendMarkup}
    ${edgeMarkup}
    ${routeMarkup}
    ${nodeMarkup}
  `;

  caption.textContent = state.currentRoute
    ? state.currentRoute.ui.caption
    : state.focusedNodeId
      ? `当前定位：${getNodeName(state.focusedNodeId)}。`
      : "当前展示的是室外节点分布；室内段会在右侧步骤卡片中说明。";
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

async function apiGet(url) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });
  return handleApiResponse(response);
}

async function apiPost(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
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

