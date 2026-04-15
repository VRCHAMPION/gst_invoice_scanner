# GST Invoice Scanner - Future Roadmap
*Proposed on: 2026-04-14*

These are the priority features to pitch and implement when continuing development:

1. **Duplicate Detection Alerts:** If a user tries to upload an invoice with an `Invoice Number` and `Seller GSTIN` that already exists in their database, the frontend should immediately warn them: "This invoice looks like a duplicate. Are you sure?"
2. **Graceful Session Expiration:** Currently, if the backend JWT token expires, API calls might silently fail or just act weird. We should add a global fetch interceptor that smoothly catches 401 Unauthorized errors, alerts the user "Your session expired," and redirects them to the login screen.
3. **Skeleton Loading States:** Replace plain loading spinners with modern "Skeleton Loaders" (the grey shimmering boxes you see on YouTube or LinkedIn) when fetching the history/analytics page. It makes the app feel much faster and more premium.
4. **Vendor Performance Ratings:** Add a simple "Trust Score" or "Red Flag" system for vendors based on how often their invoices have GST mismatches or low health scores.
5. **Export to Tally/ERP format:** Generating an export specifically strictly formatted for "Tally ERP 9" (the standard accounting software in India) would make this a killer app for Indian accountants.
