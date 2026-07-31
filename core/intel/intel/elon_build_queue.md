
### ELON-2026-07-29-001 — Local Service Provider Search - Angi Integration
- **Status:** 🟡 QUEUED
- **Date:** 2026-07-29
- **What:** Integrate Angi's API to surface local service provider listings with reviews and contact information.
- **Why:** Ability to surface localized, service-specific business listings with reviews and contact information relevant to a user's immediate needs.
- **How:** Implement new API client in `src/services/provider_search/angi_api.rs` to fetch data, and update `src/modules/search_discovery/search_handler.rs` to process and display results.
- **Effort:** MED · **Allowlisted:** NO
- **A5 Fit:** SERVES_CLIENTS — This enhances current client utility by providing local service provider data, but doesn't directly build horizontal AI patterns.
- **A9:** FLAG_FOR_COMMANDER — YES - Angi API is a paid service. Estimating $500/month for moderate usage. · ROI: Potential for increased user engagement and task completion by providing direct access to local service providers. Could lead to higher client retention if users find value in this feature.
- **ELON:** _So, we're basically building a digital Yellow Pages with Yelp reviews? Groundbreaking._


### ELON-2026-07-29-002 — Local Service Provider Search - Yelp Integration
- **Status:** 🟡 QUEUED
- **Date:** 2026-07-29
- **What:** Integrate Yelp's API to provide local service provider search results including reviews and contact details.
- **Why:** Ability to surface localized, service-specific business listings with reviews and contact information relevant to a user's immediate needs.
- **How:** Develop a Yelp API client in `src/services/provider_search/yelp_api.rs` and modify `src/modules/search_discovery/search_handler.rs` to incorporate Yelp data into search results.
- **Effort:** MED · **Allowlisted:** NO
- **A5 Fit:** SERVES_CLIENTS — Similar to Angi, this directly benefits current clients with more provider options but offers limited platform-level AI incubation.
- **A9:** FLAG_FOR_COMMANDER — YES - Yelp API has tiered pricing. Assuming a $750/month tier for sufficient query volume. · ROI: Similar to Angi, this aims to improve user utility and retention by offering more options for finding local services. Redundant functionality with Angi integration if not carefully managed.
- **ELON:** _More reviews? Because what we really need is more ways to procrastinate by reading about plumbers._


### ELON-2026-07-29-003 — Local Service Provider Search - Real Yellow Pages Integration
- **Status:** 🟡 QUEUED
- **Date:** 2026-07-29
- **What:** Integrate The Real Yellow Pages API for localized service provider listings and contact information.
- **Why:** Ability to surface localized, service-specific business listings with reviews and contact information relevant to a user's immediate needs.
- **How:** Create a new module in `src/services/provider_search/yellow_pages_api.rs` to interact with their API, and update `src/modules/search_discovery/search_handler.rs` to merge these results.
- **Effort:** MED · **Allowlisted:** NO
- **A5 Fit:** SERVES_CLIENTS — This adds another direct client-facing feature for local providers; it doesn't advance our AI incubator mandate.
- **A9:** FLAG_FOR_COMMANDER — YES - Real Yellow Pages API is a paid service. Estimating $400/month. · ROI: Further redundancy in service provider search. While it adds another data source, the ROI is questionable if Angi and Yelp already cover the core need. Risk of feature bloat without clear differentiation.
- **ELON:** _The Real Yellow Pages? Are we time traveling back to 1995?_


### ELON-2026-07-29-004 — Local Service Provider Search - Yelp (Additional)
- **Status:** 🟡 QUEUED
- **Date:** 2026-07-29
- **What:** Enhance local service provider search by integrating Yelp's review data.
- **Why:** Ability to surface localized, service-specific business listings with reviews and contact information relevant to a user's immediate needs.
- **How:** Refactor `src/services/provider_search/yelp_api.rs` to handle additional review metadata and update `src/modules/search_discovery/search_handler.rs` for richer display.
- **Effort:** LOW · **Allowlisted:** NO
- **A5 Fit:** ? — 
- **A9:** ? —  · ROI: 
- **ELON:** _Seriously, Yelp again? Are we just going to scrape the entire internet for 'plumbers'?_


### ELON-2026-07-29-005 — Local Service Provider Search - Angi (Additional)
- **Status:** 🟡 QUEUED
- **Date:** 2026-07-29
- **What:** Expand local service provider search capabilities by integrating additional data points from Angi.
- **Why:** Ability to surface localized, service-specific business listings with reviews and contact information relevant to a user's immediate needs.
- **How:** Update `src/services/provider_search/angi_api.rs` to fetch new data fields and modify `src/modules/search_discovery/search_handler.rs` to display them.
- **Effort:** LOW · **Allowlisted:** NO
- **A5 Fit:** ? — 
- **A9:** ? —  · ROI: 
- **ELON:** _More Angi data. Because the first Angi integration wasn't enough to satisfy our overwhelming need for contractor reviews._


### ELON-2026-07-29-006 — Local Service Provider Search - Plumber Directory Integration
- **Status:** 🟡 QUEUED
- **Date:** 2026-07-29
- **What:** Incorporate listings from the Plumber Directory API for localized service provider search.
- **Why:** Ability to surface localized, service-specific business listings with reviews and contact information relevant to a user's immediate needs.
- **How:** Create a new API client in `src/services/provider_search/plumber_directory_api.rs` and integrate its output into `src/modules/search_discovery/search_handler.rs`.
- **Effort:** MED · **Allowlisted:** NO
- **A5 Fit:** ? — 
- **A9:** ? —  · ROI: 
- **ELON:** _A dedicated plumber directory? This feels like a feature someone built in their garage. Let's hope it's not as buggy._
