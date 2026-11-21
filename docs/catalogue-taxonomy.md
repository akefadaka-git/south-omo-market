# South Omo Market — Product and service catalogue (A3)

This document defines the MVP catalogue scope for seller-created listings. It is a catalogue specification, not a claim that every subcategory is already enabled in the API. The current API exposes six broad seeded categories; finer subcategory selection, category-specific fields and translations are implementation work in A3.

## 1. Products and goods

### Livestock and animal products
- Cattle: bulls, cows, oxen, heifers and calves
- Goats
- Sheep
- Poultry and eggs
- Camels and pack animals where locally traded
- Beehives, beeswax and other lawful beekeeping products
- Raw milk, butter and other locally produced dairy

### Agricultural produce
- Cereals: maize, sorghum, teff, wheat and barley
- Pulses: beans, peas, chickpeas and lentils
- Oilseeds: sesame, sunflower and groundnuts
- Vegetables: tomatoes, onions, peppers, cabbage, potatoes and leafy vegetables
- Fruits: mangoes, bananas, papayas, avocados, citrus and seasonal fruits
- Coffee and other locally grown cash crops
- Seeds, seedlings, nursery plants and animal feed

### Food and household consumables
- Honey
- Grain, flour, spices and cooking ingredients
- Prepared foods, snacks and non-alcoholic drinks
- Packaged groceries and household consumables
- Soap, cleaning and hygiene products

### Retail and manufactured goods
- Clothing, traditional garments, shoes and accessories
- Household goods, cookware, bedding and furniture
- Phones, chargers, small electronics and accessories
- Solar lamps, small solar kits and batteries
- Building materials, doors, windows and fittings
- Hand tools, farm tools, irrigation supplies and spare parts
- Bicycle, motorcycle and vehicle parts and accessories

## 2. Services

### Agriculture and livestock services
- Farm labour, planting, weeding and harvesting
- Ploughing, tractor and farm-equipment hire
- Irrigation installation and repair
- Seedling, nursery and crop-care services
- Beekeeping support and hive services
- Animal husbandry and livestock handling
- Veterinary and animal-health services, listed only by appropriately qualified providers
- Livestock weighing and market preparation

### Trades, repair and construction
- Masonry, building and renovation
- Carpentry, furniture making and repair
- Plumbing and water-system repair
- Electrical installation and repair
- Welding and metal fabrication
- Solar-system installation and repair
- Phone and electronics repair
- Vehicle and motorcycle mechanics
- Tailoring, shoe repair and garment alterations

### Personal, household and community services
- Hairdressing and barber services
- Laundry, cleaning and domestic services
- Catering, food preparation and event support
- Photography, printing and document services
- Tutoring, language and skills training
- Childcare and elder-support services, subject to applicable safeguards
- Translation and interpretation

### Business and professional services
- Bookkeeping and basic accounting
- Business support and administration
- Design, marketing and printing
- IT, phone and digital support
- Licensed legal, engineering or other professional services where applicable

### Local mobility, accommodation and rentals
- Locally operated passenger transport services advertised by their providers
- Equipment, tools, tents, chairs and event-item rentals
- Agricultural machinery rentals
- Shop, workspace and accommodation listings
- Residential and commercial property rentals where legally permitted

## 3. Work opportunities

- Farm and seasonal work
- Shop and market work
- Skilled trade vacancies
- Hospitality and service work
- Apprenticeships and short-term work

Job posts must identify the employer, location, work type, pay basis and contact route. The platform must prohibit recruitment fees, misleading vacancies and discriminatory listings.

## 4. Listing attributes and buyer-facing UI

Common fields:
- Listing title and category
- Description in Amharic, Maale or English
- Price in ETB, or “Negotiable” / “Request price”
- Quantity and unit where relevant
- Condition: new, used, refurbished or not applicable
- Location, seller/business name and preferred contact method
- Up to the configured image limit; no public image exposure before moderation
- Availability: available, temporarily unavailable or sold/fulfilled

Category-specific fields should be added incrementally:
- Produce: crop, variety, quantity, unit, grade, harvest date and season
- Livestock: species, sex, approximate age, health/disclosure notes and count
- Retail goods: brand/model, condition, size and warranty if any
- Services: service area, experience/qualification, price basis and availability
- Rentals: asset, rental period, rate, deposit terms and condition
- Jobs: employer, role, work location, schedule, pay basis and closing date

Enhanced discovery UI:
- Search by title and description
- Category shortcuts and grouped category browser
- South Omo location filter
- Sort by newest and price
- Listing cards with photo, price, category and location
- Clear empty, loading, offline and retry states
- Accessible touch targets, readable typography and low-data image loading
- Amharic-first interface with Maale and English support after human translation review

## 5. Commercial and safety boundaries

- MVP settlement remains direct buyer-to-seller payment, normally cash or a mutually agreed direct method.
- No wallet, escrow, crypto, credit, platform-held funds or transaction commission.
- No platform delivery fleet or fulfilment promise.
- The marketplace is a listing and contact platform; sellers remain responsible for product accuracy, lawful sale, pricing and fulfilment.
- Prohibit illegal goods, counterfeit goods, weapons, controlled substances, wildlife products, stolen goods, deceptive listings and prohibited services.
- Apply moderation, report/block workflows, seller accountability and audit logging before public launch.
- Do not imply professional licensing or certification unless verified.
- The catalogue must be validated with the 30-seller, 30-buyer and 5-trader field pilot before monetization or commercial activation.

## 6. Implementation status

- Existing broad API categories: livestock, agriculture, food and groceries, shops and products, services, property/equipment/rentals.
- Existing app capabilities: public listing discovery, category/location filters, listing detail, buyer inquiry, seller onboarding/inbox, listing drafts and moderation workflow.
- Implemented on the current feature branch: public discovery filters by category and location; server-side search across listing title, description and location; stable newest-first and price ascending/descending sorting; listing summaries expose description/category metadata; mobile search submits to the API; the UI exposes sort choices and a load-more pagination control backed by the API limit/offset contract; clear-search and no-match states remain available.
- Implemented on the feature branch: additive migration `0007_catalogue_expansion` adds 20 further leaf categories covering camels/pack animals, beekeeping, coffee/cash crops, farm inputs/irrigation, honey/spices, grain/flour, building materials, solar products, vehicle parts, farm machinery, veterinary services, construction trades, household/personal services, business/digital services, local transport, education/community services, event rentals, workspace rentals, hospitality jobs and apprenticeships.
- Existing `0006_category_attributes` subcategories plus `0007_catalogue_expansion` now provide category-specific schemas across livestock, agriculture, food, retail, services, rentals and jobs. The API remains authoritative and validates required values, text limits, numeric ranges, booleans, choices, unknown keys and malformed schemas.
- Still open: migration execution and backend/mobile test execution on the exact current head; field-pilot review of the catalogue; reviewed Amharic and Maale translations and human language approval. The new categories intentionally have null Amharic/Maale labels until approved translations exist.
