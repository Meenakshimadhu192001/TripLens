/**
 * TripLens - Application Logic, NLP Processing & AI Dynamic Recommendation Renderer
 * Middleman decision intelligence platform linking niche travel agencies with travelers.
 */

document.addEventListener("DOMContentLoaded", () => {
  // App State Store
  const state = {
    currentScreen: localStorage.getItem("triplens_user") ? "home" : "login",
    previousScreen: "login",
    history: [localStorage.getItem("triplens_user") ? "home" : "login"],
    selectedPackageId: "hp002",
    activeDestFilter: "Himachal (Shimla/Manali)",
    userPrompt: TRIPWISE_DATA.defaultRequest,
    preferences: { ...TRIPWISE_DATA.defaultPreferences },
    costBreakdownOpen: false,
    searchResults: null,
    selectedPackageData: null,
    isGuest: false  // true when user chose "Continue as Guest"
  };

  // DOM Elements Cache
  const elements = {
    screens: document.querySelectorAll(".screen"),
    stepTracker: document.getElementById("step-tracker"),
    stepItems: document.querySelectorAll(".step-item"),
    brandHomeLink: document.getElementById("brand-home-link"),
    btnQuickCompare: document.getElementById("btn-quick-compare"),

    // Home Screen
    destPillsContainer: document.getElementById("dest-pills-container"),
    homeHeroImg: document.getElementById("home-hero-img"),
    heroBadgeTag: document.getElementById("hero-badge-tag"),
    userTripPrompt: document.getElementById("user-trip-prompt"),
    suggestionChips: document.getElementById("suggestion-chips"),
    btnFindMyTrip: document.getElementById("btn-find-my-trip"),

    // Preferences Screen
    aiExtractionSummary: document.getElementById("ai-extraction-summary"),
    dispPrefBudget: document.getElementById("disp-pref-budget"),
    dispPrefDuration: document.getElementById("disp-pref-duration"),
    dispPrefDestination: document.getElementById("disp-pref-destination"),
    dispPrefFrom: document.getElementById("disp-pref-from"),
    dispPrefTravelers: document.getElementById("disp-pref-travelers"),
    dispPrefPace: document.getElementById("disp-pref-pace"),
    btnConfirmFindTrips: document.getElementById("btn-confirm-find-trips"),

    // Results Screen
    resultsDestTabs: document.getElementById("results-dest-tabs"),
    packagesCardsList: document.getElementById("packages-cards-list"),
    activeFilterPills: document.getElementById("active-filter-pills"),
    btnCompareShortcutResults: document.getElementById("btn-compare-shortcut-results"),

    // Details Screen
    detailsHeroImg: document.getElementById("details-hero-img"),
    detailsBadgesContainer: document.getElementById("details-badges-container"),
    detailsTitle: document.getElementById("details-title"),
    detailsSubtitle: document.getElementById("details-subtitle"),
    detailsAgencyType: document.getElementById("details-agency-type"),
    detailsAgencyName: document.getElementById("details-agency-name"),
    detailsSourceUrlLink: document.getElementById("details-source-url-link"),
    dispDetailsDuration: document.getElementById("disp-details-duration"),
    dispDetailsTravelers: document.getElementById("disp-details-travelers"),
    dispDetailsFrom: document.getElementById("disp-details-from"),
    dispDetailsFocus: document.getElementById("disp-details-focus"),
    dispDetailsPace: document.getElementById("disp-details-pace"),
    detailsScoreFit: document.getElementById("details-score-fit"),
    detailsScoreValue: document.getElementById("details-score-value"),
    detailsScoreTrust: document.getElementById("details-score-trust"),
    detailsCostBase: document.getElementById("details-cost-base"),
    detailsCostAdditional: document.getElementById("details-cost-additional"),
    detailsCostEffective: document.getElementById("details-cost-effective"),
    btnToggleCostBreakdown: document.getElementById("btn-toggle-cost-breakdown"),
    costItemsContainer: document.getElementById("cost-items-container"),
    detailsInclusionsList: document.getElementById("details-inclusions-list"),
    detailsExclusionsList: document.getElementById("details-exclusions-list"),

    // Reviews Section on Details Screen
    detailsReviewsRatingTitle: document.getElementById("details-reviews-rating-title"),
    detailsReviewsCountSubtitle: document.getElementById("details-reviews-count-subtitle"),
    detailsReviewsSourceLink: document.getElementById("details-reviews-source-link"),
    detailsCustomerReviewsList: document.getElementById("details-customer-reviews-list"),

    btnNavToItinerary: document.getElementById("btn-nav-to-itinerary"),
    btnNavToTrust: document.getElementById("btn-nav-to-trust"),
    btnNavToCompare: document.getElementById("btn-nav-to-compare"),
    btnDetailsToCompare: document.getElementById("btn-details-to-compare"),

    // Itinerary Screen
    itineraryPkgLabel: document.getElementById("itinerary-pkg-label"),
    itineraryTimelineList: document.getElementById("itinerary-timeline-list"),
    btnItineraryToTrust: document.getElementById("btn-itinerary-to-trust"),

    // Trust Insights Screen
    trustPkgLabel: document.getElementById("trust-pkg-label"),
    trustDispScore: document.getElementById("trust-disp-score"),
    trustAspectsContainer: document.getElementById("trust-aspects-container"),
    trustSentimentBar: document.getElementById("trust-sentiment-bar"),
    trustSentimentLegend: document.getElementById("trust-sentiment-legend"),
    btnTrustToCompare: document.getElementById("btn-trust-to-compare"),

    // Compare Screen
    compareTableContainer: document.getElementById("compare-table-container"),

    // Modals
    whyMatchModal: document.getElementById("why-match-modal"),
    whyModalTitle: document.getElementById("why-modal-title"),
    whyModalFitPercent: document.getElementById("why-modal-fit-percent"),
    whyModalReasonsList: document.getElementById("why-modal-reasons-list"),
    btnWhyModalProceed: document.getElementById("btn-why-modal-proceed"),
    btnCloseWhyModal: document.getElementById("btn-close-why-modal"),

    editPrefModal: document.getElementById("edit-pref-modal"),
    editPrefForm: document.getElementById("edit-pref-form"),
    editFieldMinBudgetSlider: document.getElementById("edit-field-min-budget-slider"),
    editMinBudgetBadge: document.getElementById("edit-min-budget-badge"),
    editFieldMaxBudgetSlider: document.getElementById("edit-field-max-budget-slider"),
    editMaxBudgetBadge: document.getElementById("edit-max-budget-badge"),
    editFieldDuration: document.getElementById("edit-field-duration"),
    editFieldDestination: document.getElementById("edit-field-destination"),
    editFieldFrom: document.getElementById("edit-field-from"),
    editFieldTravelers: document.getElementById("edit-field-travelers"),
    editFieldPace: document.getElementById("edit-field-pace"),
    btnCloseEditModal: document.getElementById("btn-close-edit-modal"),
    btnCancelEdit: document.getElementById("btn-cancel-edit"),

    // Toast
    appToast: document.getElementById("app-toast"),
    toastIcon: document.getElementById("toast-icon"),
    toastText: document.getElementById("toast-text")
  };

  // ---- TripLens API Integration ----
  // A relative URL works locally and after deployment behind a proxy.
  const API_BASE_URL = "";

  async function fetchExtractPreferences(promptText) {
    const res = await fetch(`${API_BASE_URL}/extract-preferences`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: promptText })
    });
    if (!res.ok) throw new Error(`extract-preferences failed: ${res.status}`);
    const data = await res.json();
    return data.preferences;
  }

  async function fetchSearch(apiPrefs, promptText) {
    const res = await fetch(`${API_BASE_URL}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...apiPrefs, prompt: promptText, top_k: 10 })
    });
    if (!res.ok) throw new Error(`search failed: ${res.status}`);
    const data = await res.json();
    return data.results || [];
  }

  async function learnPrompt(apiPrefs, promptText) {
    const res = await fetch(`${API_BASE_URL}/api/learn-prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...apiPrefs, prompt: promptText, user_id: "U001" })
    });
    if (!res.ok) throw new Error(`learn-prompt failed: ${res.status}`);
  }

  function mapApiPrefsToUiPrefs(apiPrefs) {
    return {
      minBudget: apiPrefs.budget_min ?? 8000,
      maxBudget: apiPrefs.budget_max ?? 30000,
      duration: apiPrefs.duration_days ?? state.preferences.duration,
      from: apiPrefs.start_location || state.preferences.from,
      travelers: apiPrefs.travelers ?? state.preferences.travelers,
      destination: apiPrefs.destination_region || state.preferences.destination,
      pace: apiPrefs.pace || state.preferences.pace,
      interests: apiPrefs.interests || []
    };
  }

  function mapUiPrefsToApiPrefs(uiPrefs) {
    return {
      destination_region: uiPrefs.destination === "all" ? null : uiPrefs.destination,
      start_location: uiPrefs.from,
      duration_days: uiPrefs.duration,
      budget_min: uiPrefs.minBudget,
      budget_max: uiPrefs.maxBudget,
      travelers: uiPrefs.travelers,
      pace: uiPrefs.pace,
      interests: uiPrefs.interests || []
    };
  }

  // Fields with no real data source stay null rather than being invented.
  function mapApiPackageToUiPkg(apiPkg) {
    const destText = (apiPkg.destinations || "").toLowerCase();
    return {
      id: apiPkg.package_id,
      title: apiPkg.package_name || "Untitled Package",
      agency: apiPkg.agency_name || "Agency not specified",
      sourceUrl: apiPkg.source_url_or_doc || "#",
      destination: apiPkg.destinations || "",
      duration: apiPkg.duration_days ? `${apiPkg.duration_days} Days` : "Duration not specified",
      price: apiPkg.price || 0,
      pace: apiPkg.pace || null,
      hotel: null,
      hotelRating: null,
      rating: null,
      costBreakdown: null,
      badge: null,
      badgeIcon: "",
      image: destText.includes("kerala") ? "/assets/hero-kerala.svg" : "/assets/hero-himachal.svg",
      dynamicFitScore: apiPkg.fit_score,
      dynamicReasons: apiPkg.reasons || [],
      costBreakdown: { packagePrice: apiPkg.price || 0, estimatedAdditional: 0, effectiveTotal: apiPkg.price || 0, items: [] }
    };
  }

  function mapApiDetailToUiPkg(apiPkg, rankedPkg = {}) {
    const itinerary = (apiPkg.itinerary || []).map((day) => ({
      day: day.day_number,
      route: day.stops || "Route details unavailable",
      tagline: day.activity_type || "Scheduled activities",
      intensity: day.transit_hours >= 6 ? "High" : day.transit_hours >= 3 ? "Moderate" : "Low",
      transitHours: day.transit_hours != null ? `${day.transit_hours} hrs` : "Not specified",
      distanceKm: day.distance_km != null ? `${day.distance_km} km` : null,
      meals: day.meals_included_today || "Not specified",
      warnings: day.flagged_for_verification ? [day.flagged_for_verification] : [],
      activities: String(day.activities || "Activities not specified").split(/\s*;\s*/)
    }));
    const price = Number(apiPkg.price || 0);
    return {
      ...rankedPkg,
      id: apiPkg.package_id, packageCode: apiPkg.package_id,
      title: apiPkg.package_name || "Untitled package",
      subtitle: apiPkg.destinations || "Destination details not specified",
      agency: apiPkg.agency_name || "Agency not specified",
      agencyType: apiPkg.data_source || "Package data source",
      sourceUrl: apiPkg.source_url_or_doc || "#",
      destination: apiPkg.destinations || "",
      duration: `${apiPkg.duration_days || "—"} Days / ${apiPkg.duration_nights || "—"} Nights`,
      price, origin: apiPkg.start_location || "Not specified",
      pace: apiPkg.itinerary_pace_inferred || apiPkg.itinerary_pace || "Not specified",
      hotel: (apiPkg.accommodation || []).map((a) => a.hotel_name || a.accommodation_category).filter(Boolean).join(", ") || null,
      hotelRating: null,
      image: String(apiPkg.destinations || "").toLowerCase().includes("kerala") ? "/assets/hero-kerala.svg" : "/assets/hero-himachal.svg",
      badge: "DATA-BASED MATCH", badgeIcon: "✓",
      overview: { focusText: apiPkg.theme_clean || apiPkg.theme || "Not specified", paceText: apiPkg.itinerary_pace_inferred || apiPkg.itinerary_pace || "Not specified" },
      valueScore: Math.round(apiPkg.data_completeness_score || 0), trustScore: "N/A", rating: null,
      costBreakdown: { packagePrice: price, estimatedAdditional: 0, effectiveTotal: price, items: [] },
      inclusions: apiPkg.inclusions || [], exclusions: apiPkg.exclusions || [], itinerary,
      itinerary_available: apiPkg.itinerary_available, reviews_available: false,
      dynamicFitScore: rankedPkg.dynamicFitScore || 0, dynamicReasons: rankedPkg.dynamicReasons || []
    };
  }

  async function loadPackageDetail(packageId) {
    const rankedPkg = (state.searchResults || []).find((pkg) => pkg.id === packageId) || {};
    try {
      const res = await fetch(`${API_BASE_URL}/package/${encodeURIComponent(packageId)}`);
      if (!res.ok) throw new Error(`package failed: ${res.status}`);
      state.selectedPackageData = mapApiDetailToUiPkg(await res.json(), rankedPkg);
    } catch (err) {
      console.error("package detail failed:", err);
      state.selectedPackageData = rankedPkg.id ? rankedPkg : null;
      showToast("Could not load full package details.", "⚠");
    }
  }

  function getSelectedPackage() {
    return state.selectedPackageData || TRIPWISE_DATA.packages.find((p) => p.id === state.selectedPackageId) || TRIPWISE_DATA.packages[0];
  }

  /**
   * Helper: Show Toast Notification
   */
  let toastTimer = null;
  function showToast(message, icon = "✓") {
    if (toastTimer) clearTimeout(toastTimer);
    elements.toastText.textContent = message;
    elements.toastIcon.textContent = icon;
    elements.appToast.classList.add("show");
    toastTimer = setTimeout(() => {
      elements.appToast.classList.remove("show");
    }, 2800);
  }

  /**
   * Screen Router
   */
  function navigateTo(screenName, recordHistory = true) {
    if (!document.getElementById(`screen-${screenName}`)) {
      console.warn(`Screen ${screenName} not found.`);
      return;
    }

    if (recordHistory && state.currentScreen !== screenName) {
      state.previousScreen = state.currentScreen;
      state.history.push(screenName);
    }

    state.currentScreen = screenName;

    const screens = document.querySelectorAll(".screen");
    screens.forEach((screen) => {
      if (screen.id === `screen-${screenName}`) {
        screen.classList.add("active");
      } else {
        screen.classList.remove("active");
      }
    });

    elements.stepItems.forEach((item) => {
      const step = item.getAttribute("data-step");
      if (step === screenName) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    window.scrollTo({ top: 0, behavior: "smooth" });

    if (screenName === "details") {
      renderPackageDetails();
    } else if (screenName === "itinerary") {
      renderItineraryScreen();
    } else if (screenName === "trust") {
      renderTrustInsightsScreen();
    } else if (screenName === "results") {
      renderResultsScreen();
    } else if (screenName === "compare") {
      renderCompareScreen();
    }
  }

  /**
   * Render Preset Suggestion Chips
   */
  function renderSuggestionChips() {
    if (!elements.suggestionChips) return;
    elements.suggestionChips.innerHTML = "";

    TRIPWISE_DATA.suggestionChips.forEach((chip, idx) => {
      const btn = document.createElement("button");
      btn.className = `chip-btn ${idx === 0 ? "active" : ""}`;
      btn.dataset.chip = chip.label;
      btn.textContent = chip.label;

      btn.addEventListener("click", () => {
        elements.suggestionChips.querySelectorAll(".chip-btn").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        elements.userTripPrompt.value = chip.query;
        state.userPrompt = chip.query;
        if (chip.destination) {
          state.activeDestFilter = chip.destination;
          updateDestinationTheme(chip.destination);
        }
        if (chip.minBudget) state.preferences.minBudget = chip.minBudget;
        if (chip.maxBudget) state.preferences.maxBudget = chip.maxBudget;
        if (chip.duration) state.preferences.duration = chip.duration;
        parseNaturalLanguage(chip.query);
        showToast(`Loaded preset: "${chip.label}"`);
      });

      elements.suggestionChips.appendChild(btn);
    });
  }

  /**
   * Update Hero Theme Image & Badges based on Destination
   */
  function updateDestinationTheme(dest) {
    if (dest.includes("Himachal")) {
      elements.homeHeroImg.src = "/assets/hero-himachal.svg";
      elements.heroBadgeTag.textContent = "✨ Himachal Mountain Escapes • TripLens Niche Intelligence";
    } else if (dest.includes("Kerala")) {
      elements.homeHeroImg.src = "/assets/hero-kerala.svg";
      elements.heroBadgeTag.textContent = "🌿 Kerala Backwater Trails • TripLens Niche Intelligence";
    } else {
      elements.homeHeroImg.src = "/assets/hero-himachal.svg";
      elements.heroBadgeTag.textContent = "🌐 All Independent Travel Agency Packages • TripLens";
    }
  }

  /**
   * Parse Natural Language Prompt into Structured Preferences
   */
  function parseNaturalLanguage(promptText) {
    const text = promptText.toLowerCase();
    const parsed = { ...state.preferences };

    // Range or Single Budget Parse
    const rangeMatch = text.match(/(?:between|from)?\s*(?:₹|rs.?)?\s*(\d{1,2}(?:,\d{3})+|\d{4,6})\s*(?:and|to|-)\s*(?:₹|rs.?)?\s*(\d{1,2}(?:,\d{3})+|\d{4,6})/i);
    if (rangeMatch) {
      const minVal = parseInt(rangeMatch[1].replace(/,/g, ""), 10);
      const maxVal = parseInt(rangeMatch[2].replace(/,/g, ""), 10);
      if (!isNaN(minVal) && !isNaN(maxVal)) {
        parsed.minBudget = Math.min(minVal, maxVal);
        parsed.maxBudget = Math.max(minVal, maxVal);
      }
    } else {
      const singleMatch = text.match(/(?:under|below|budget|within|max|₹|rs.?)\s*(?:₹|rs.?)?\s*(\d{1,2}(?:,\d{3})+|\d{4,6})/i);
      if (singleMatch) {
        const val = parseInt(singleMatch[1].replace(/,/g, ""), 10);
        if (!isNaN(val)) {
          parsed.maxBudget = val;
          parsed.minBudget = Math.max(8000, val - 8000);
        }
      }
    }

    // Duration Parse
    const durationMatch = text.match(/(\d+)\s*(?:-|\s)?\s*day/i);
    if (durationMatch) {
      const days = parseInt(durationMatch[1], 10);
      if (days >= 2 && days <= 14) {
        parsed.duration = days;
      }
    }

    // Destination Parse
    if (text.includes("shimla") || text.includes("manali") || text.includes("himachal") || text.includes("solang") || text.includes("kasol") || text.includes("amritsar") || text.includes("jibhi")) {
      parsed.destination = "Himachal (Shimla/Manali)";
      state.activeDestFilter = "Himachal (Shimla/Manali)";
    } else if (text.includes("kerala") || text.includes("munnar") || text.includes("alleppey") || text.includes("wayanad") || text.includes("kovalam")) {
      parsed.destination = "Kerala";
      state.activeDestFilter = "Kerala";
    }

    // Origin / Departure City
    if (text.includes("delhi")) {
      parsed.from = "Delhi";
    } else if (text.includes("chandigarh")) {
      parsed.from = "Chandigarh";
    } else if (text.includes("bangalore") || text.includes("bengaluru")) {
      parsed.from = "Bangalore";
    } else if (text.includes("kochi")) {
      parsed.from = "Kochi";
    }

    // Travel Pace
    if (text.includes("relaxed") || text.includes("leisure") || text.includes("slow")) {
      parsed.pace = "Relaxed";
    } else if (text.includes("active") || text.includes("express") || text.includes("circuit") || text.includes("full")) {
      parsed.pace = "Active";
    }

    state.preferences = parsed;
    updatePreferencesDisplay();
    updateDestinationTheme(parsed.destination);
  }

  /**
   * Update Preferences UI on Screen 2
   */
  function updatePreferencesDisplay() {
    const pref = state.preferences;
    elements.aiExtractionSummary.innerHTML = `
      <strong>TripLens AI Extraction:</strong> "${pref.duration}-day ${pref.pace.toLowerCase()} ${pref.destination} trip from ${pref.from} for ${pref.travelers} traveler${pref.travelers > 1 ? "s" : ""} between ₹${pref.minBudget.toLocaleString("en-IN")} and ₹${pref.maxBudget.toLocaleString("en-IN")} budget."
    `;
    elements.dispPrefBudget.textContent = `₹${pref.minBudget.toLocaleString("en-IN")} – ₹${pref.maxBudget.toLocaleString("en-IN")}`;
    elements.dispPrefDuration.textContent = `${pref.duration} days`;
    elements.dispPrefDestination.textContent = pref.destination.split(" ")[0];
    elements.dispPrefFrom.textContent = pref.from;
    elements.dispPrefTravelers.textContent = `${pref.travelers} traveler${pref.travelers > 1 ? "s" : ""}`;
    elements.dispPrefPace.textContent = pref.pace;
  }

  /**
   * AI Smart Recommendation Engine
   * Evaluates fit score smartly the way a human would decide!
   */
  function evaluateSmartFit(pkg) {
    const pref = state.preferences;
    let score = pkg.fitScore || 90;
    const reasons = [...(pkg.whyMatches?.reasons || [])];

    // Budget fit check
    const p = pkg.price;
    if (p >= pref.minBudget && p <= pref.maxBudget) {
      score += 4;
    } else if (p > pref.maxBudget) {
      const diff = p - pref.maxBudget;
      if (diff <= 4000) {
        score -= 2;
        reasons.unshift({
          text: `🤖 Human AI Recommendation: ₹${diff.toLocaleString("en-IN")} above max budget, but worth considering for additional days/sightseeing & high ${pkg.rating}★ agency rating!`,
          positive: true
        });
      } else {
        score -= 6;
      }
    } else if (p < pref.minBudget) {
      reasons.unshift({
        text: `💰 Under your minimum budget by ₹${(pref.minBudget - p).toLocaleString("en-IN")}, leaving extra budget for activities!`,
        positive: true
      });
    }

    // Rating boost
    if (pkg.rating >= 4.8) {
      score += 2;
    }

    return {
      finalScore: Math.min(99, Math.max(65, score)),
      reasons: reasons
    };
  }

  /**
   * Get Filtered Packages with Smart AI Recommendations
   */
  function getFilteredPackages() {
    if (Array.isArray(state.searchResults)) {
      return state.searchResults;
    }

    let filtered = TRIPWISE_DATA.packages;

    if (state.activeDestFilter && state.activeDestFilter !== "all") {
      filtered = filtered.filter((pkg) => pkg.destination === state.activeDestFilter);
    }

    filtered = filtered.map((pkg) => {
      const smart = evaluateSmartFit(pkg);
      return {
        ...pkg,
        dynamicFitScore: smart.finalScore,
        dynamicReasons: smart.reasons
      };
    });

    return filtered.sort((a, b) => b.dynamicFitScore - a.dynamicFitScore);
  }

  /**
   * Render Packages on Results Screen
   */
  function renderResultsScreen() {
    const packages = getFilteredPackages();
    elements.packagesCardsList.innerHTML = "";

    // Update Filter Summary Pills
    const pref = state.preferences;
    elements.activeFilterPills.innerHTML = `
      <span class="filter-pill">📍 ${pref.from}</span>
      <span class="filter-pill">📅 ${pref.duration} Days</span>
      <span class="filter-pill">💰 ₹${pref.minBudget.toLocaleString("en-IN")} – ₹${pref.maxBudget.toLocaleString("en-IN")}</span>
      <span class="filter-pill">⛰️ ${state.activeDestFilter}</span>
    `;

    if (packages.length === 0) {
      elements.packagesCardsList.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem; background: var(--bg-surface); border-radius: var(--radius-lg); border: 1px dashed var(--border-color);">
          <h3>No packages match your specific filters</h3>
          <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.4rem;">Try selecting "All Packages" or adjusting your budget range.</p>
        </div>
      `;
      return;
    }

    packages.forEach((pkg, index) => {
      const isTop = index === 0;

      // Human-like smart recommendation tag if applicable
      const smartReason = pkg.dynamicReasons.find((r) => r.text.includes("Human AI") || r.text.includes("AI Recommendation"));

      const card = document.createElement("div");
      card.className = `package-card ${isTop ? "highlighted" : ""}`;
      card.dataset.packageId = pkg.id;

      card.innerHTML = `
        <div class="package-card-media">
          <img src="${pkg.image}" alt="${pkg.title}" class="package-card-img" loading="lazy">
          ${pkg.badge ? `<span class="package-badge-top">${pkg.badgeIcon} ${pkg.badge}</span>` : ""}
          <div class="package-fit-badge">
            <span class="fit-dot"></span>
            <span>${pkg.dynamicFitScore}% Fit Match</span>
          </div>
        </div>

        <div class="package-card-body">
          <!-- Agency & Code Header -->
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.35rem;">
            <div style="display: flex; align-items: center; gap: 0.35rem;">
              <span style="font-size: 0.72rem; font-weight: 800; color: var(--primary); background: var(--primary-light); padding: 0.2rem 0.55rem; border-radius: var(--radius-pill);">
                ${pkg.agency}
              </span>
              <span style="font-size: 0.68rem; font-weight: 700; color: var(--text-muted);">${pkg.rating ? `★ ${pkg.rating} / 5` : "Rating not available"}</span>
            </div>
            <a href="${pkg.sourceUrl}" target="_blank" rel="noopener noreferrer" class="btn-source-url" onclick="event.stopPropagation();">
              🌐 Source ↗
            </a>
          </div>

          <div class="package-title-area">
            <h3 class="package-card-title">${pkg.title}</h3>
            <div class="package-card-hotel">
              <span>🏨</span>
              <span>${pkg.hotel ? pkg.hotel : "Hotel details not available"}${pkg.hotelRating ? ` • <strong>★ ${pkg.hotelRating}</strong>` : ""}</span>
            </div>
          </div>

          <div class="package-specs-row">
            <span class="spec-pill">📅 ${pkg.duration}</span>
            <span class="spec-pill">👥 ${state.preferences.travelers} Travelers</span>
            <span class="spec-pill">🧘 ${pkg.pace || "Pace not specified"}</span>
          </div>

          ${smartReason ? `
            <div class="ai-human-rec-tag">
              <span>💡</span>
              <span>${smartReason.text}</span>
            </div>
          ` : ""}

          <div class="package-price-row">
            <div class="price-group">
              <span class="price-currency">₹</span>
              <span class="price-val">${pkg.price.toLocaleString("en-IN")}</span>
            </div>
            <span class="price-sub">${pkg.costBreakdown ? `Effective Total: ₹${pkg.costBreakdown.effectiveTotal.toLocaleString("en-IN")}` : "Price as listed by agency"}</span>
          </div>

          <div class="package-card-actions">
            <button class="btn-view-details" data-action="view-details" data-id="${pkg.id}">
              View Full Package & Reviews →
            </button>
            <div class="btn-secondary-actions-row">
              <button class="btn-why-match" data-action="why-match" data-id="${pkg.id}">
                ✨ Why this matches
              </button>
              <button class="btn-card-compare" data-action="compare" data-id="${pkg.id}">
                ⚖️ Compare
              </button>
            </div>
          </div>
        </div>
      `;

      elements.packagesCardsList.appendChild(card);
    });

    attachPackageCardListeners();
  }

  /**
   * Package Card Action Listeners
   */
  function attachPackageCardListeners() {
    const viewButtons = elements.packagesCardsList.querySelectorAll('[data-action="view-details"]');
    const whyButtons = elements.packagesCardsList.querySelectorAll('[data-action="why-match"]');
    const compareButtons = elements.packagesCardsList.querySelectorAll('[data-action="compare"]');

    viewButtons.forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        state.selectedPackageId = e.currentTarget.dataset.id;
        await loadPackageDetail(state.selectedPackageId);
        navigateTo("details");
      });
    });

    whyButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        openWhyThisMatchesModal(e.currentTarget.dataset.id);
      });
    });

    compareButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        state.selectedPackageId = e.currentTarget.dataset.id;
        navigateTo("compare");
      });
    });
  }

  /**
   * Render Package Details Screen
   */
  function renderPackageDetails() {
    const pkg = getSelectedPackage();

    // Image & Header
    elements.detailsHeroImg.src = pkg.image;
    elements.detailsHeroImg.alt = pkg.title;
    elements.detailsTitle.textContent = pkg.title;
    elements.detailsSubtitle.textContent = pkg.subtitle;

    // Agency & Source URL
    elements.detailsAgencyType.textContent = `${pkg.agencyType} • Code: ${pkg.packageCode}`;
    elements.detailsAgencyName.textContent = pkg.agency;
    elements.detailsSourceUrlLink.href = pkg.sourceUrl;
    elements.detailsSourceUrlLink.textContent = `🌐 View Original Source on ${pkg.agency} ↗`;

    // Badges
    const smart = evaluateSmartFit(pkg);
    elements.detailsBadgesContainer.innerHTML = `
      <span class="package-badge-top" style="position: static; font-size: 0.72rem;">${pkg.badgeIcon} ${pkg.badge}</span>
      <span class="package-fit-badge" style="position: static; font-size: 0.72rem;">
        <span class="fit-dot"></span>
        <span>${smart.finalScore}% Fit Match</span>
      </span>
    `;

    // Overview Specs
    elements.dispDetailsDuration.textContent = pkg.duration;
    elements.dispDetailsTravelers.textContent = `${state.preferences.travelers} Travelers`;
    elements.dispDetailsFrom.textContent = `From ${pkg.origin}`;
    elements.dispDetailsFocus.textContent = pkg.overview.focusText;
    elements.dispDetailsPace.textContent = pkg.overview.paceText;

    // Scores
    elements.detailsScoreFit.textContent = `${smart.finalScore}%`;
    elements.detailsScoreValue.textContent = `${pkg.valueScore}/100`;
    elements.detailsScoreTrust.textContent = pkg.trustScore === "N/A" ? "N/A" : `${pkg.trustScore}/100`;

    // Effective Cost
    elements.detailsCostBase.textContent = `₹${pkg.costBreakdown.packagePrice.toLocaleString("en-IN")}`;
    elements.detailsCostAdditional.textContent = pkg.reviews_available === false && pkg.costBreakdown.estimatedAdditional === 0
      ? "Not disclosed"
      : `+₹${pkg.costBreakdown.estimatedAdditional.toLocaleString("en-IN")}`;
    elements.detailsCostEffective.textContent = `₹${pkg.costBreakdown.effectiveTotal.toLocaleString("en-IN")}`;

    renderCostBreakdownItems(pkg);

    // Inclusions & Exclusions
    elements.detailsInclusionsList.innerHTML = pkg.inclusions.map((item) => `<li>${item}</li>`).join("");
    elements.detailsExclusionsList.innerHTML = pkg.exclusions.map((item) => `<li>${item}</li>`).join("");

    // Dedicated Customer Reviews Section
    renderCustomerReviews(pkg);
  }

  /**
   * Render Dedicated Reviews Section on Details Screen
   */
  function renderCustomerReviews(pkg) {
    if (!elements.detailsCustomerReviewsList) return;

    if (pkg.reviews_available === false) {
      elements.detailsReviewsRatingTitle.textContent = "Reviews not available";
      elements.detailsReviewsCountSubtitle.textContent = "This dataset does not include verified review data for this package.";
      elements.detailsReviewsSourceLink.href = pkg.sourceUrl;
      elements.detailsReviewsSourceLink.textContent = "🌐 View provider source ↗";
      elements.detailsCustomerReviewsList.innerHTML = "<p style=\"color: var(--text-muted); font-size: 0.85rem;\">TripLens does not invent ratings, review counts, or customer quotes when they are not supplied by the source.</p>";
      return;
    }

    elements.detailsReviewsRatingTitle.textContent = `⭐ ${pkg.rating} / 5 Customer Rating`;
    elements.detailsReviewsCountSubtitle.textContent = `Verified reviews for ${pkg.title} provided by ${pkg.agency}`;
    elements.detailsReviewsSourceLink.href = pkg.sourceUrl;
    elements.detailsReviewsSourceLink.textContent = `🌐 ${pkg.agency} Source ↗`;

    const reviews = pkg.trustInsights?.reviewsList || [
      { name: "Rahul S.", rating: 5.0, date: "Aug 2026", comment: `Excellent trip organized by ${pkg.agency}! Highly professional cab drivers and top hotel stays.` },
      { name: "Priya M.", rating: 4.8, date: "Jul 2026", comment: "Super smooth experience. Highly recommended for couples and families!" }
    ];

    elements.detailsCustomerReviewsList.innerHTML = reviews
      .map(
        (rev) => `
        <div class="review-quote-card">
          <div>
            <div class="review-quote-header">
              <span class="reviewer-name">${rev.name}</span>
              <span class="review-date">${rev.date}</span>
            </div>
            <div class="review-rating-stars">
              ${"★".repeat(Math.floor(rev.rating))} (${rev.rating} / 5)
            </div>
            <p class="review-comment-text">"${rev.comment}"</p>
          </div>
          <div style="font-size: 0.68rem; color: var(--text-subtle); margin-top: 0.5rem; text-align: right;">
            Verified Traveler • ${pkg.agency}
          </div>
        </div>
      `
      )
      .join("");
  }

  /**
   * Render Cost Breakdown Items
   */
  function renderCostBreakdownItems(pkg) {
    if (!state.costBreakdownOpen) {
      elements.costItemsContainer.style.display = "none";
      elements.btnToggleCostBreakdown.textContent = "View Breakdown ▼";
      return;
    }

    elements.costItemsContainer.style.display = "block";
    elements.btnToggleCostBreakdown.textContent = "Hide Breakdown ▲";

    let html = "";
    pkg.costBreakdown.items.forEach((item) => {
      html += `
        <div class="cost-item-row">
          <span>${item.label}</span>
          <span style="font-weight: 700; color: var(--text-main);">₹${item.amount.toLocaleString("en-IN")}</span>
        </div>
      `;
    });

    html += `
      <div class="cost-item-row total-row">
        <span>${pkg.reviews_available === false ? "Listed package price (no extras disclosed)" : "Effective Total (Honest estimate)"}</span>
        <span>₹${pkg.costBreakdown.effectiveTotal.toLocaleString("en-IN")}</span>
      </div>
    `;

    elements.costItemsContainer.innerHTML = html;
  }

  /**
   * Render Itinerary Intelligence Screen
   */
  function renderItineraryScreen() {
    const pkg = getSelectedPackage();
    elements.itineraryPkgLabel.textContent = `${pkg.agency} • ${pkg.title} (${pkg.duration})`;
    elements.itineraryTimelineList.innerHTML = "";

    if (!pkg.itinerary || pkg.itinerary.length === 0) {
      elements.itineraryTimelineList.innerHTML = "<p style=\"color: var(--text-muted);\">A day-by-day itinerary was not supplied for this package.</p>";
      return;
    }

    pkg.itinerary.forEach((dayItem) => {
      const card = document.createElement("div");
      card.className = "timeline-day-card";

      const intensityClass =
        dayItem.intensity.toLowerCase() === "low"
          ? "intensity-low"
          : dayItem.intensity.toLowerCase() === "high"
            ? "intensity-high"
            : "intensity-moderate";

      const intensityIcon =
        dayItem.intensity.toLowerCase() === "low"
          ? "🟢"
          : dayItem.intensity.toLowerCase() === "high"
            ? "🔴"
            : "🟠";

      card.innerHTML = `
        <div class="timeline-node"></div>
        <div class="timeline-day-header">
          <div class="day-badge-title">
            <span class="day-number-tag">Day ${dayItem.day}</span>
            <span class="day-route-title">${dayItem.route} — ${dayItem.tagline}</span>
          </div>
        </div>

        <div class="day-indicators-row" style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.5rem 0;">
          <span class="intensity-pill ${intensityClass}">
            ${intensityIcon} Intensity: <strong>${dayItem.intensity}</strong>
          </span>
          <span class="freetime-pill">
            ⏱️ Transit: <strong>${dayItem.transitHours || "Local"}</strong>
          </span>
          ${dayItem.distanceKm ? `<span class="freetime-pill">🚗 Distance: <strong>${dayItem.distanceKm}</strong></span>` : ""}
          <span class="freetime-pill">🍽️ Meals: <strong>${dayItem.meals || "Included"}</strong></span>
        </div>

        ${dayItem.warnings && dayItem.warnings.length > 0 ? `
          <div style="background: #FEF3C7; border: 1px solid #F59E0B; padding: 0.5rem 0.75rem; border-radius: 8px; font-size: 0.75rem; color: #92400E; margin-bottom: 0.6rem;">
            ${dayItem.warnings.map((w) => `<div>${w}</div>`).join("")}
          </div>
        ` : ""}

        <ul class="day-activities-list">
          ${dayItem.activities.map((act) => `
            <li>
              <span class="activity-dot"></span>
              <span>${act}</span>
            </li>
          `).join("")}
        </ul>
      `;

      elements.itineraryTimelineList.appendChild(card);
    });
  }

  /**
   * Render Trust & Review Sentiment Screen
   */
  function renderTrustInsightsScreen() {
    const pkg = getSelectedPackage();
    if (!pkg.trustInsights) {
      elements.trustPkgLabel.textContent = `${pkg.agency} • ${pkg.title}`;
      elements.trustDispScore.textContent = "N/A";
      elements.trustSentimentBar.innerHTML = "";
      elements.trustSentimentLegend.innerHTML = "<span class=\"legend-item\">Review and sentiment data were not provided for this package.</span>";
      elements.trustAspectsContainer.innerHTML = "<p style=\"color: var(--text-muted);\">Trust insights require verified review data. No rating or sentiment has been inferred.</p>";
      return;
    }
    elements.trustPkgLabel.textContent = `${pkg.agency} • ${pkg.title} (★ ${pkg.rating} / 5 • ${pkg.trustInsights.totalReviews} Verified Traveler Reviews)`;
    elements.trustDispScore.textContent = pkg.trustInsights.score;

    const sent = pkg.trustInsights.sentiment;
    elements.trustSentimentBar.innerHTML = `
      <div class="sentiment-seg seg-positive" style="width: ${sent.positive}%;" title="${sent.positive}% Positive"></div>
      <div class="sentiment-seg seg-neutral" style="width: ${sent.neutral}%;" title="${sent.neutral}% Neutral"></div>
      <div class="sentiment-seg seg-negative" style="width: ${sent.negative}%;" title="${sent.negative}% Negative"></div>
    `;

    elements.trustSentimentLegend.innerHTML = `
      <span class="legend-item"><span class="legend-dot" style="background: #10B981;"></span> <strong>${sent.positive}%</strong> Positive</span>
      <span class="legend-item"><span class="legend-dot" style="background: #F59E0B;"></span> <strong>${sent.neutral}%</strong> Neutral</span>
      <span class="legend-item"><span class="legend-dot" style="background: #EF4444;"></span> <strong>${sent.negative}%</strong> Negative</span>
    `;

    elements.trustAspectsContainer.innerHTML = "";

    pkg.trustInsights.aspects.forEach((aspect) => {
      const card = document.createElement("div");
      card.className = "aspect-card";

      const isPositive = aspect.sentimentType === "positive";
      const statusClass = isPositive ? "status-positive" : "status-mixed";
      const statusIcon = isPositive ? "✓ Positive Sentiment" : "⚠️ Mixed Signals";

      card.innerHTML = `
        <div class="aspect-card-header">
          <div class="aspect-title-group">
            <span class="aspect-icon">${aspect.icon}</span>
            <span class="aspect-name">${aspect.name}</span>
          </div>
          <span class="aspect-score-pill">★ ${aspect.score}</span>
        </div>

        <div class="aspect-sentiment-status ${statusClass}">
          ${statusIcon}
        </div>

        <div class="aspect-positives-title">Verified Positive Signals:</div>
        <ul class="aspect-signals-list">
          ${aspect.positives.map((p) => `<li>${p}</li>`).join("")}
        </ul>

        ${aspect.concern ? `
          <div class="aspect-concern-box">
            <div class="concern-label">
              <span>⚠️</span> Potential Concern / Caveat
            </div>
            <div class="concern-text">${aspect.concern}</div>
          </div>
        ` : ""}
      `;

      elements.trustAspectsContainer.appendChild(card);
    });
  }

  /**
   * Render Cross-Provider Decision Matrix / Compare Screen
   */
  function renderCompareScreen() {
    const packages = getFilteredPackages().slice(0, 4);
    if (packages.length === 0) return;

    let tableHtml = `
      <table class="compare-table" id="comparison-table">
        <thead>
          <tr>
            <th style="min-width: 135px;">Metric</th>
            ${packages.map((pkg, i) => `
              <th class="${i === 0 ? "col-highlighted" : ""}">
                <div class="col-header-cell">
                  ${pkg.badge ? `<span class="col-best-badge">${pkg.badgeIcon} ${pkg.badge}</span>` : ""}
                  <span class="col-header-title">${pkg.title}</span>
                  <span style="font-size: 0.7rem; font-weight: 800; color: var(--primary);">${pkg.agency}</span>
                  <a href="${pkg.sourceUrl}" target="_blank" class="btn-source-url" style="margin-top: 0.25rem;">Source ↗</a>
                </div>
              </th>
            `).join("")}
          </tr>
        </thead>
        <tbody>
          <!-- Base Price -->
          <tr>
            <td class="row-label">Advertised Price</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""} metric-val">₹${pkg.price.toLocaleString("en-IN")}</td>
            `).join("")}
          </tr>

          <!-- Effective Total Cost -->
          <tr>
            <td class="row-label">Effective Total Cost</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""} metric-val" style="font-weight: 800; color: var(--primary);">
                ₹${pkg.costBreakdown.effectiveTotal.toLocaleString("en-IN")}
              </td>
            `).join("")}
          </tr>

          <!-- Customer Rating & Reviews -->
          <tr>
            <td class="row-label">Customer Rating</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""} metric-val score-bold" style="color: #D97706;">
                ${pkg.rating != null && pkg.trustInsights ? `⭐ ${pkg.rating} / 5 (${pkg.trustInsights.totalReviews} reviews)` : "Not available"}
              </td>
            `).join("")}
          </tr>

          <!-- AI Fit Match -->
          <tr>
            <td class="row-label">AI Fit Match Score</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""} metric-val score-bold" style="color: #065F46;">
                ${pkg.dynamicFitScore}%
              </td>
            `).join("")}
          </tr>

          <!-- Provider Agency & Source -->
          <tr>
            <td class="row-label">Agency & Source URL</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""} metric-val">
                <strong>${pkg.agency}</strong><br/>
                <a href="${pkg.sourceUrl}" target="_blank" class="btn-source-url" style="display: inline-block; margin-top: 4px;">Original Source ↗</a>
              </td>
            `).join("")}
          </tr>

          <!-- Duration -->
          <tr>
            <td class="row-label">Duration & Stays</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""} metric-val">${pkg.duration}</td>
            `).join("")}
          </tr>

          <!-- Hotel Quality -->
          <tr>
            <td class="row-label">Hotel Category</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""} metric-val">${pkg.hotel || "Not specified"}${pkg.hotelRating ? ` (★ ${pkg.hotelRating})` : ""}</td>
            `).join("")}
          </tr>

          <!-- Action Buttons -->
          <tr>
            <td class="row-label">Select Package</td>
            ${packages.map((pkg, i) => `
              <td class="${i === 0 ? "td-highlighted" : ""}">
                <button class="btn-choose-col ${i === 0 ? "primary" : ""}" data-select-pkg="${pkg.id}">
                  Inspect Details
                </button>
              </td>
            `).join("")}
          </tr>
        </tbody>
      </table>
    `;

    elements.compareTableContainer.innerHTML = tableHtml;

    // Attach listeners on dynamically generated select buttons
    elements.compareTableContainer.querySelectorAll("[data-select-pkg]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        state.selectedPackageId = btn.getAttribute("data-select-pkg");
        await loadPackageDetail(state.selectedPackageId);
        showToast("Selected package for detailed inspection");
        navigateTo("details");
      });
    });
  }

  /**
   * Open "Why this matches" Modal
   */
  function openWhyThisMatchesModal(pkgId) {
    const pkg = (state.searchResults || []).find((p) => p.id === pkgId) || TRIPWISE_DATA.packages.find((p) => p.id === pkgId) || TRIPWISE_DATA.packages[0];
    const smart = pkg.dynamicFitScore ? { finalScore: pkg.dynamicFitScore, reasons: pkg.dynamicReasons || [] } : evaluateSmartFit(pkg);

    elements.whyModalTitle.textContent = `Why ${pkg.title} matches`;
    elements.whyModalFitPercent.textContent = `${smart.finalScore}% Fit Match`;

    elements.whyModalReasonsList.innerHTML = smart.reasons
      .map(
        (r) => `
        <li style="${r.positive ? "" : "color: #92400E;"}">
          ${r.text}
        </li>
      `
      )
      .join("");

    elements.btnWhyModalProceed.onclick = async () => {
      closeWhyThisMatchesModal();
      state.selectedPackageId = pkg.id;
      await loadPackageDetail(pkg.id);
      navigateTo("details");
    };

    elements.whyMatchModal.classList.add("active");
    elements.whyMatchModal.setAttribute("aria-hidden", "false");
  }

  function closeWhyThisMatchesModal() {
    elements.whyMatchModal.classList.remove("active");
    elements.whyMatchModal.setAttribute("aria-hidden", "true");
  }

  /**
   * Open Edit Preference Modal
   */
  function openEditPrefModal() {
    if (elements.editFieldMinBudgetSlider) {
      elements.editFieldMinBudgetSlider.value = state.preferences.minBudget;
      elements.editMinBudgetBadge.textContent = `₹${state.preferences.minBudget.toLocaleString("en-IN")}`;
    }
    if (elements.editFieldMaxBudgetSlider) {
      elements.editFieldMaxBudgetSlider.value = state.preferences.maxBudget;
      elements.editMaxBudgetBadge.textContent = `₹${state.preferences.maxBudget.toLocaleString("en-IN")}`;
    }
    elements.editFieldDuration.value = state.preferences.duration;
    elements.editFieldDestination.value = state.preferences.destination;
    elements.editFieldFrom.value = state.preferences.from;
    elements.editFieldTravelers.value = state.preferences.travelers;
    elements.editFieldPace.value = state.preferences.pace;

    elements.editPrefModal.classList.add("active");
    elements.editPrefModal.setAttribute("aria-hidden", "false");
  }

  function closeEditPrefModal() {
    elements.editPrefModal.classList.remove("active");
    elements.editPrefModal.setAttribute("aria-hidden", "true");
  }

  /**
   * Event Listeners Setup
   */
  function attachEventListeners() {
    // Brand Link
    elements.brandHomeLink.addEventListener("click", () => navigateTo("home"));

    // Quick Compare
    elements.btnQuickCompare.addEventListener("click", () => navigateTo("compare"));

    // Destination Pills on Home Screen
    if (elements.destPillsContainer) {
      elements.destPillsContainer.querySelectorAll(".dest-pill").forEach((pill) => {
        pill.addEventListener("click", () => {
          elements.destPillsContainer.querySelectorAll(".dest-pill").forEach((p) => p.classList.remove("active"));
          pill.classList.add("active");
          const dest = pill.getAttribute("data-dest");
          state.activeDestFilter = dest;
          if (dest !== "all") {
            state.preferences.destination = dest;
          }
          updateDestinationTheme(dest);
          showToast(`Destination scope set to ${dest === "all" ? "All Packages" : dest}`);
        });
      });
    }

    // Results Destination Tabs
    if (elements.resultsDestTabs) {
      elements.resultsDestTabs.querySelectorAll(".tab-btn").forEach((tab) => {
        tab.addEventListener("click", () => {
          elements.resultsDestTabs.querySelectorAll(".tab-btn").forEach((t) => t.classList.remove("active"));
          tab.classList.add("active");
          state.activeDestFilter = tab.getAttribute("data-tab");
          renderResultsScreen();
        });
      });
    }

    // Step Tracker
    elements.stepItems.forEach((item) => {
      item.addEventListener("click", () => {
        navigateTo(item.getAttribute("data-step"));
      });
    });

    // Home Prompt CTA
    elements.btnFindMyTrip.addEventListener("click", async () => {
      const promptValue = elements.userTripPrompt.value.trim();
      if (!promptValue) {
        navigateTo("preferences");
        return;
      }
      state.userPrompt = promptValue;
      showToast("Analyzing your trip request...");
      try {
        const apiPrefs = await fetchExtractPreferences(promptValue);
        state.preferences = mapApiPrefsToUiPrefs(apiPrefs);
        updatePreferencesDisplay();
        updateDestinationTheme(state.preferences.destination || "all");
      } catch (err) {
        console.error("extract-preferences failed, falling back to local parsing:", err);
        parseNaturalLanguage(promptValue);
      }
      navigateTo("preferences");
    });

    // Edit Preferences
    document.querySelectorAll(".btn-edit-pref").forEach((btn) => {
      btn.addEventListener("click", () => openEditPrefModal());
    });

    if (elements.editFieldMinBudgetSlider) {
      elements.editFieldMinBudgetSlider.addEventListener("input", (e) => {
        const val = parseInt(e.target.value, 10);
        elements.editMinBudgetBadge.textContent = `₹${val.toLocaleString("en-IN")}`;
      });
    }

    if (elements.editFieldMaxBudgetSlider) {
      elements.editFieldMaxBudgetSlider.addEventListener("input", (e) => {
        const val = parseInt(e.target.value, 10);
        elements.editMaxBudgetBadge.textContent = `₹${val.toLocaleString("en-IN")}`;
      });
    }

    elements.editPrefForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const minB = parseInt(elements.editFieldMinBudgetSlider.value, 10);
      const maxB = parseInt(elements.editFieldMaxBudgetSlider.value, 10);
      state.preferences.minBudget = Math.min(minB, maxB);
      state.preferences.maxBudget = Math.max(minB, maxB);
      state.preferences.duration = parseInt(elements.editFieldDuration.value, 10);
      state.preferences.destination = elements.editFieldDestination.value;
      state.preferences.from = elements.editFieldFrom.value;
      state.preferences.travelers = parseInt(elements.editFieldTravelers.value, 10);
      state.preferences.pace = elements.editFieldPace.value;

      state.activeDestFilter = state.preferences.destination;

      updatePreferencesDisplay();
      closeEditPrefModal();
      showToast("Preferences updated! Recalculating AI matches...");
    });

    elements.btnConfirmFindTrips.addEventListener("click", async () => {
      showToast("Searching real packages...");
      try {
        const apiPrefs = mapUiPrefsToApiPrefs(state.preferences);
        await learnPrompt(apiPrefs, state.userPrompt);
        const results = await fetchSearch(apiPrefs, state.userPrompt);
        state.searchResults = results.map(mapApiPackageToUiPkg);
      } catch (err) {
        console.error("search failed:", err);
        state.searchResults = [];
        showToast("Could not reach TripLens API — is uvicorn running?", "⚠");
      }
      navigateTo("results");
    });
    elements.btnCompareShortcutResults.addEventListener("click", () => navigateTo("compare"));

    elements.btnToggleCostBreakdown.addEventListener("click", () => {
      state.costBreakdownOpen = !state.costBreakdownOpen;
      const pkg = getSelectedPackage();
      renderCostBreakdownItems(pkg);
    });

    elements.btnNavToItinerary.addEventListener("click", () => navigateTo("itinerary"));
    elements.btnNavToTrust.addEventListener("click", () => navigateTo("trust"));
    elements.btnNavToCompare.addEventListener("click", () => navigateTo("compare"));
    elements.btnDetailsToCompare.addEventListener("click", () => navigateTo("compare"));

    elements.btnItineraryToTrust.addEventListener("click", () => navigateTo("trust"));
    elements.btnTrustToCompare.addEventListener("click", () => navigateTo("compare"));

    document.querySelectorAll("[data-back-to]").forEach((btn) => {
      btn.addEventListener("click", () => navigateTo(btn.getAttribute("data-back-to")));
    });

    elements.btnCloseWhyModal.addEventListener("click", closeWhyThisMatchesModal);
    elements.btnCloseEditModal.addEventListener("click", closeEditPrefModal);
    elements.btnCancelEdit.addEventListener("click", closeEditPrefModal);

    elements.whyMatchModal.addEventListener("click", (e) => {
      if (e.target === elements.whyMatchModal) closeWhyThisMatchesModal();
    });
    elements.editPrefModal.addEventListener("click", (e) => {
      if (e.target === elements.editPrefModal) closeEditPrefModal();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeWhyThisMatchesModal();
        closeEditPrefModal();
      }
    });
  }

    // --- Personal Travel Memory & Next-Trip Handlers ---
    const profileModal = document.getElementById("modal-travel-profile-overlay");
    const logTripModal = document.getElementById("modal-log-trip-overlay");
    const btnTravelProfile = document.getElementById("btn-travel-profile");
    const btnCloseProfile = document.getElementById("btn-close-profile");
    const btnSaveProfileSettings = document.getElementById("btn-save-profile-settings");
    const btnResetProfile = document.getElementById("btn-reset-profile");
    const btnOpenLogTrip = document.getElementById("btn-open-log-trip");
    const btnCloseLogTrip = document.getElementById("btn-close-log-trip");
    const btnCancelLogTrip = document.getElementById("btn-cancel-log-trip");
    const formLogTrip = document.getElementById("form-log-trip");
    const togglePersonalization = document.getElementById("toggle-personalization");
    const nextTripCardsGrid = document.getElementById("next-trip-cards-grid");

    let currentNextTripMode = "preferences";

    async function loadNextTripSuggestions(mode = "preferences") {
      currentNextTripMode = mode;
      document.querySelectorAll(".next-trip-modes .dest-pill").forEach(b => {
        b.classList.toggle("active", b.dataset.mode === mode);
      });

      if (!nextTripCardsGrid) return;
      nextTripCardsGrid.innerHTML = `<div style="grid-column: 1/-1; color: var(--text-subtle); padding: 1.5rem; text-align: center;">Analyzing travel history and generating suggestions...</div>`;

      try {
        const res = await fetch(`${API_BASE_URL}/api/next-trip-suggestions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: "U001", mode: mode, top_k: 4 })
        });
        if (!res.ok) throw new Error("Next trip fetch failed");
        const data = await res.json();
        renderNextTripCards(data.results || [], data.is_cold_start);
      } catch (err) {
        console.error("Next trip error:", err);
        nextTripCardsGrid.innerHTML = `<div style="grid-column: 1/-1; color: var(--text-subtle); padding: 1rem; text-align: center;">Could not load next-trip suggestions. Ensure uvicorn server is running.</div>`;
      }
    }

    function renderNextTripCards(results, isColdStart) {
      if (!results || results.length === 0) {
        nextTripCardsGrid.innerHTML = `<div style="grid-column: 1/-1; color: var(--text-subtle); padding: 1rem;">No recommendations found. Try logging a completed trip to train your profile!</div>`;
        return;
      }

      nextTripCardsGrid.innerHTML = results.map(item => {
        const exp = item.explanation || {};
        const matched = (exp.matched_reasons || []).map(r => `<div style="font-size: 0.73rem; color: #10b981; margin-bottom: 0.2rem;">✓ ${r}</div>`).join("");
        const concerns = (exp.potential_concerns || []).map(c => `<div style="font-size: 0.73rem; color: #f59e0b; margin-top: 0.2rem;">⚠ ${c}</div>`).join("");

        return `
          <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; display: flex; flex-direction: column; justify-space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
                <span style="font-size: 0.7rem; font-weight: 700; color: var(--primary); background: rgba(59,130,246,0.1); padding: 0.15rem 0.4rem; border-radius: 4px;">
                  ${item.novelty_score >= 80 ? "✨ UNEXPLORED" : "🌿 PREFERENCE FIT"}
                </span>
                <span style="font-size: 0.85rem; font-weight: 700; color: #10b981;">${item.fit_score}% FIT</span>
              </div>
              <h4 style="font-size: 0.95rem; font-weight: 700; margin: 0 0 0.2rem 0;">${item.package_name}</h4>
              <div style="font-size: 0.78rem; color: var(--text-subtle); margin-bottom: 0.6rem;">
                📍 ${item.destinations} • ⏱️ ${item.duration_days} Days • ₹${Number(item.price || 0).toLocaleString('en-IN')}
              </div>
              <div style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 0.6rem; margin-bottom: 0.8rem;">
                <div style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.3rem;">Why TripLens Suggested This</div>
                ${matched || '<div style="font-size: 0.73rem; color: var(--text-subtle);">Popular curated package</div>'}
                ${concerns}
              </div>
            </div>
            <button class="btn-secondary btn-view-pkg-detail" data-id="${item.package_id}" style="width: 100%; font-size: 0.78rem; padding: 0.4rem;">
              View Package Details
            </button>
          </div>
        `;
      }).join("");

      nextTripCardsGrid.querySelectorAll(".btn-view-pkg-detail").forEach(btn => {
        btn.addEventListener("click", () => {
          const pkgId = btn.dataset.id;
          state.selectedPackageId = pkgId;
          loadPackageDetail(pkgId).then(() => navigateTo("details"));
        });
      });
    }

    async function loadUserProfile() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/user/profile?user_id=U001`);
        if (!res.ok) return;
        const profile = await res.json();
        renderProfileModal(profile);
      } catch (e) {
        console.error("Failed to load profile:", e);
      }
    }

    async function renderProfileModal(profile) {
      document.getElementById("profile-user-id").innerText = `Traveler Profile: ${profile.user_id} (${profile.home_location})`;
      togglePersonalization.checked = profile.personalization_enabled;

      const tripsRes = await fetch(`${API_BASE_URL}/api/user/trips?user_id=U001`);
      const tripsData = tripsRes.ok ? await tripsRes.json() : { trips: [] };
      const trips = tripsData.trips || [];

      document.getElementById("profile-stats-summary").innerText = `Home: ${profile.home_location} • Completed Trips: ${trips.length} • Learned Themes: ${profile.preferred_themes.length}`;

      // Learned Badges
      const badgesContainer = document.getElementById("profile-learned-badges");
      if (profile.preferred_themes.length === 0) {
        badgesContainer.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-subtle);">No learned preferences yet. Log completed trips below to train your profile!</span>`;
      } else {
        badgesContainer.innerHTML = profile.preferred_themes.map(t => {
          const conf = (profile.confidence || {})[t] || 0.5;
          return `<span style="background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3); color: var(--primary); font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 12px;">🌿 ${t} (${Math.round(conf * 100)}% conf)</span>`;
        }).join(" ") + (profile.avoided_preferences.length > 0 ? profile.avoided_preferences.map(a => `<span style="background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: #ef4444; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 12px;">🚫 Avoid: ${a}</span>`).join(" ") : "");
      }

      // Trips Timeline
      const timelineContainer = document.getElementById("profile-trips-timeline");
      if (trips.length === 0) {
        timelineContainer.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-subtle); padding: 1rem; border: 1px dashed var(--border-subtle); border-radius: 8px; text-align: center;">Your travel history is empty. Click "+ Log Past Trip" to record completed trips!</div>`;
      } else {
        timelineContainer.innerHTML = trips.map(t => `
          <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 700; font-size: 0.88rem;">📍 ${(t.destinations || []).join(", ")}</div>
              <div style="font-size: 0.75rem; color: var(--text-subtle);">
                ${t.duration_days ? t.duration_days + ' Days • ' : ''}₹${Number(t.budget_spent_inr || 0).toLocaleString('en-IN')} • Rating: ${'⭐'.repeat(t.user_rating || 5)}
              </div>
              ${t.user_feedback ? `<div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem;">"${t.user_feedback}"</div>` : ''}
            </div>
            <button class="btn-delete-trip" data-id="${t.trip_id}" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 0.9rem;" title="Delete trip">🗑️</button>
          </div>
        `).join("");

        timelineContainer.querySelectorAll(".btn-delete-trip").forEach(btn => {
          btn.addEventListener("click", async () => {
            const tripId = btn.dataset.id;
            await fetch(`${API_BASE_URL}/api/user/trips/${tripId}`, { method: "DELETE" });
            showToast("Trip removed from history", "🗑️");
            loadUserProfile();
            loadNextTripSuggestions(currentNextTripMode);
          });
        });
      }
    }

    btnTravelProfile.addEventListener("click", () => {
      loadUserProfile();
      profileModal.setAttribute("aria-hidden", "false");
      profileModal.classList.add("active");
    });

    btnCloseProfile.addEventListener("click", () => {
      profileModal.setAttribute("aria-hidden", "true");
      profileModal.classList.remove("active");
    });

    btnSaveProfileSettings.addEventListener("click", async () => {
      const isEnabled = togglePersonalization.checked;
      await fetch(`${API_BASE_URL}/api/user/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "U001", personalization_enabled: isEnabled })
      });
      profileModal.setAttribute("aria-hidden", "true");
      profileModal.classList.remove("active");
      loadNextTripSuggestions(currentNextTripMode);
    });

    btnResetProfile.addEventListener("click", async () => {
      if (confirm("Reset all travel history and learned preferences?")) {
        await fetch(`${API_BASE_URL}/api/user/profile/reset?user_id=U001`, { method: "DELETE" });
        showToast("Travel history reset.", "ℹ");
        loadUserProfile();
        loadNextTripSuggestions(currentNextTripMode);
      }
    });

    btnOpenLogTrip.addEventListener("click", () => {
      logTripModal.setAttribute("aria-hidden", "false");
      logTripModal.classList.add("active");
    });

    const closeLogTrip = () => {
      logTripModal.setAttribute("aria-hidden", "true");
      logTripModal.classList.remove("active");
    };

    btnCloseLogTrip.addEventListener("click", closeLogTrip);
    btnCancelLogTrip.addEventListener("click", closeLogTrip);

    formLogTrip.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        user_id: "U001",
        package_id: document.getElementById("log-package-id").value || null,
        destinations: document.getElementById("log-destinations").value,
        duration_days: parseInt(document.getElementById("log-duration").value, 10),
        budget_spent_inr: parseFloat(document.getElementById("log-budget").value) || 25000,
        themes: document.getElementById("log-themes").value.split(",").map(s => s.trim()).filter(Boolean),
        user_rating: parseFloat(document.getElementById("log-rating").value),
        liked: document.getElementById("log-liked").value.split(",").map(s => s.trim()).filter(Boolean),
        disliked: document.getElementById("log-disliked").value.split(",").map(s => s.trim()).filter(Boolean),
        source: "manual_entry"
      };

      try {
        const res = await fetch(`${API_BASE_URL}/api/user/trips`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          showToast("Trip memory & feedback saved!", "✨");
          closeLogTrip();
          loadUserProfile();
          loadNextTripSuggestions(currentNextTripMode);
        }
      } catch (err) {
        console.error("Failed to save trip memory:", err);
      }
    });

    // --- Account Authentication Handlers ---
    const btnUserLogout = document.getElementById("btn-user-logout");
    const userLogoutLabel = document.getElementById("user-logout-label");
    const authModal = document.getElementById("modal-auth-overlay");
    const btnCloseAuth = document.getElementById("btn-close-auth");
    const formAuth = document.getElementById("form-auth");
    const authModalTitle = document.getElementById("auth-modal-title");
    const btnSubmitAuth = document.getElementById("btn-submit-auth");
    const authToggleMsg = document.getElementById("auth-toggle-msg");
    const authToggleLink = document.getElementById("auth-toggle-link");

    let authMode = "login";
    let currentUser = JSON.parse(localStorage.getItem("triplens_user")) || null;

    function updateAuthUi() {
      if (currentUser && btnUserLogout) {
        // Logged-in user: show "Logout (username)"
        btnUserLogout.style.display = "inline-flex";
        btnUserLogout.title = "Logout";
        userLogoutLabel.innerText = `Logout (${currentUser.email.split("@")[0]})`;
      } else if (state.isGuest && btnUserLogout) {
        // Guest user: show "Exit Guest Mode" to return to login
        btnUserLogout.style.display = "inline-flex";
        btnUserLogout.title = "Exit guest mode and return to login";
        userLogoutLabel.innerText = "Exit Guest Mode";
      } else if (btnUserLogout) {
        btnUserLogout.style.display = "none";
      }
    }

    if (btnUserLogout) {
      btnUserLogout.addEventListener("click", () => {
        if (currentUser) {
          if (confirm("Are you sure you want to log out?")) {
            currentUser = null;
            localStorage.removeItem("triplens_user");
            state.isGuest = false;
            updateAuthUi();
            showToast("Logged out successfully.");
            navigateTo("login");
          }
        } else if (state.isGuest) {
          // Guest exits back to login screen
          state.isGuest = false;
          updateAuthUi();
          showToast("Returned to login screen.");
          navigateTo("login");
        }
      });
    }

    if (btnCloseAuth) {
      btnCloseAuth.addEventListener("click", () => {
        authModal.setAttribute("aria-hidden", "true");
        authModal.classList.remove("active");
      });
    }

    if (authToggleLink) {
      authToggleLink.addEventListener("click", (e) => {
        e.preventDefault();
        authMode = authMode === "login" ? "register" : "login";
        if (authMode === "register") {
          authModalTitle.innerText = "Create Traveler Account";
          btnSubmitAuth.innerText = "Register Account";
          authToggleMsg.innerText = "Already have an account?";
          authToggleLink.innerText = "Sign In";
        } else {
          authModalTitle.innerText = "Traveler Login";
          btnSubmitAuth.innerText = "Sign In";
          authToggleMsg.innerText = "Don't have an account?";
          authToggleLink.innerText = "Register now";
        }
      });
    }

    if (formAuth) {
      formAuth.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("auth-email").value.trim();
        const password = document.getElementById("auth-password").value;

        const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
        try {
          const res = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Authentication failed");

          currentUser = { email: email, user_id: data.user_id || "U001" };
          localStorage.setItem("triplens_user", JSON.stringify(currentUser));
          updateAuthUi();
          authModal.setAttribute("aria-hidden", "true");
          authModal.classList.remove("active");
          showToast(authMode === "login" ? "Logged in successfully!" : "Account registered successfully!", "✨");
          loadUserProfile();
          loadNextTripSuggestions(currentNextTripMode);
        } catch (err) {
          showToast(err.message, "⚠");
        }
      });
    }

    // --- Login Screen (Screen 0) Handlers ---
    const formScreenAuth = document.getElementById("form-screen-auth");
    const screenAuthEmail = document.getElementById("screen-auth-email");
    const screenAuthPassword = document.getElementById("screen-auth-password");
    const screenAuthBtnText = document.getElementById("screen-auth-btn-text");
    const screenAuthToggleMsg = document.getElementById("screen-auth-toggle-msg");
    const screenAuthToggleLink = document.getElementById("screen-auth-toggle-link");
    const btnSkipLogin = document.getElementById("btn-skip-login");

    let screenAuthMode = "login";

    if (screenAuthToggleLink) {
      screenAuthToggleLink.addEventListener("click", (e) => {
        e.preventDefault();
        screenAuthMode = screenAuthMode === "login" ? "register" : "login";
        if (screenAuthMode === "register") {
          screenAuthBtnText.innerText = "Register Account & Continue";
          screenAuthToggleMsg.innerText = "Already have an account?";
          screenAuthToggleLink.innerText = "Sign In";
        } else {
          screenAuthBtnText.innerText = "Sign In & Continue to TripLens";
          screenAuthToggleMsg.innerText = "Don't have an account?";
          screenAuthToggleLink.innerText = "Register now";
        }
      });
    }

    if (formScreenAuth) {
      formScreenAuth.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = screenAuthEmail.value.trim();
        const password = screenAuthPassword.value;

        const endpoint = screenAuthMode === "login" ? "/api/auth/login" : "/api/auth/register";
        try {
          const res = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Authentication failed");

          currentUser = { email: email, user_id: data.user_id || "U001" };
          localStorage.setItem("triplens_user", JSON.stringify(currentUser));
          updateAuthUi();
          showToast(screenAuthMode === "login" ? "Welcome back!" : "Account registered!", "✨");
          navigateTo("home");
          loadUserProfile();
          loadNextTripSuggestions(currentNextTripMode);
        } catch (err) {
          showToast(err.message, "⚠");
        }
      });
    }

    if (btnSkipLogin) {
      btnSkipLogin.addEventListener("click", () => {
        // Mark as guest so the "Exit Guest Mode" button shows in the header
        state.isGuest = true;
        updateAuthUi();
        showToast("Browsing as guest — sign in to save your preferences.", "👤");
        navigateTo("home");
      });
    }

    // --- Next-Trip Suggestion Mode Pill Handlers ---
    const modePrefBtn = document.getElementById("mode-pref");
    const modeNewBtn = document.getElementById("mode-new");
    const modeLastBtn = document.getElementById("mode-last");

    if (modePrefBtn) {
      modePrefBtn.addEventListener("click", () => loadNextTripSuggestions("preferences"));
    }
    if (modeNewBtn) {
      modeNewBtn.addEventListener("click", () => loadNextTripSuggestions("something_new"));
    }
    if (modeLastBtn) {
      modeLastBtn.addEventListener("click", () => loadNextTripSuggestions("similar_last"));
    }

    // Initialization
    function init() {
      updateAuthUi();
      renderSuggestionChips();
      parseNaturalLanguage(state.userPrompt);
      renderResultsScreen();
      attachEventListeners();
      loadNextTripSuggestions("preferences");
      if (state.currentScreen === "login") {
        navigateTo("login");
      }
      console.log("TripLens initialized with Personal Travel Memory & Next-Trip Engine.");
    }

    init();
  });