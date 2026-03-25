# Design System Strategy: Atmospheric Precision

## 1. Overview & Creative North Star
**Creative North Star: The Obsidian Terminal**
This design system is a study in "Atmospheric Precision." We are moving away from the generic "SaaS Dashboard" look to create an environment that feels like a high-end code editor merged with a premium editorial layout. The goal is to balance the warmth of human conversation (Group Chat) with the clinical, cold efficiency of data (Analytics).

We break the "template" feel by utilizing **Tonal Layering** rather than structural lines. The UI should feel like it was carved out of a single piece of obsidian—varying only in its matte or polished finish. We rely on extreme typographic contrast and intentional negative space to guide the eye, rather than boxes and borders.

## 2. Colors & Surface Architecture
The palette is rooted in deep blacks and tech-focused accents. We use a "Modern Family" color assignment to personify the data streams.

### The Modern Family Palette
- **Phil (Primary):** `primary` (#adc6ff) - Logical, foundational.
- **Claire (Secondary):** `secondary` (#ffb3b5) - Sharp, high-energy.
- **Haley (Tertiary):** `tertiary` (#f1c100) - Vibrant, attention-seeking.
- **Alex (Success/Logic):** `outline` (#8b90a0) / Green Tones - Calculated.
- **Luke (Error/Urgency):** `error` (#ffb4ab) - Raw, immediate.
- **Manny (Sophistication):** `primary_container` (#4b8eff) - Deep, thoughtful.

### The "No-Line" Rule
To achieve a high-end editorial feel, **1px solid borders are strictly prohibited for sectioning.** You must define boundaries through background color shifts. 
- Use `surface` (#131313) for the base canvas.
- Use `surface_container_low` (#1c1b1b) for secondary zones.
- Use `surface_container_highest` (#353534) for interactive elements like input fields or hover states.

### Surface Hierarchy & Nesting
Treat the UI as a series of nested plates. 
- **The Canvas:** `surface_dim` (#131313).
- **The Content Block:** `surface_container_low` (#1c1b1b).
- **The Floating Element:** `surface_bright` (#3a3939).
*Direction:* An Analytics Card should not have a border; it should simply be a `surface_container_high` block sitting on a `surface` background.

## 3. Typography: The Editorial Contrast
We use a dual-typeface approach to distinguish between "Human" and "Data."

- **The Human Voice (Inter):** All chat bubbles, headers, and body copy. Inter is used for its neutral, modernist clarity. Use `headline-lg` (2rem) for dashboard titles to create a bold, editorial entry point.
- **The Analytical Voice (Space Grotesk):** All numbers, timestamps, and dev-tool labels. Space Grotesk provides a "monospaced" soul that feels technical and precise without being dated.
- **Scale Intensity:** Use `display-sm` (2.25rem) for hero metrics in the sidebar. Contrast this immediately with `label-sm` (0.6875rem) for the description. This "High-Low" pairing is the hallmark of premium design.

## 4. Elevation & Depth (Non-Structural)
Since gradients and shadows are forbidden, depth must be achieved through **Tonal Stacking**.

- **The Layering Principle:** To "lift" a component, move it one step up the surface-container scale. A `surface_container_highest` bubble on a `surface_container_low` background creates a perceived lift of 4dp without a single shadow pixel.
- **The "Ghost Border" Fallback:** In high-density analytics where separation is critical, use a "Ghost Border." Apply `outline_variant` (#414755) at **15% opacity**. It should be felt, not seen.
- **Glassmorphism:** For floating overlays (like a user profile popover), use `surface_container_highest` at 80% opacity with a `20px` backdrop blur. This ensures the chat colors bleed through, maintaining the "Atmospheric" vibe.

## 5. Components

### Chat Bubbles (iMessage-Refined)
- **Sent Bubbles:** `primary_container` (#4b8eff) with `on_primary_container` text. 
- **Received Bubbles:** `surface_container_highest` (#353534) with `on_surface` text.
- **Corner Radius:** Use `xl` (1.5rem) for the outer curve. Use `sm` (0.25rem) for the "tail" corner to mimic the iMessage organic-yet-directional feel.

### Analytics Cards (Minimalist Dev-Tool)
- **Container:** No borders. `surface_container_low`.
- **Header:** Use `label-md` in `primary` color for the category name. 
- **Data:** Use Space Grotesk for the values.
- **Spacing:** Use `spacing-8` (1.75rem) internal padding to give data "room to breathe"—this is the difference between a tool and an experience.

### Input Fields
- **State:** Resting state is `surface_container_lowest`. On focus, shift to `surface_container_high`.
- **Indicator:** Use a 2px bottom bar in `primary` (#adc6ff) during focus instead of a full bounding box.

### Vertical Dividers
- Forbid 100% height lines. Use a `3px` wide vertical pill (Roundness `full`) that is only `40%` of the container height, colored with `outline_variant` at low opacity.

## 6. Do's and Don'ts

### Do:
- **Use "Space as Structure":** Use `spacing-16` and `spacing-20` to separate major dashboard sections instead of lines.
- **Color Coding by Name:** Ensure Phil's metrics always use the Blue `primary` token, and Claire's use the Pink `secondary` token. Consistency is trust.
- **Monospace Alignment:** In the analytics sidebar, ensure all numbers are right-aligned to maintain the "Dev-Tool" grid integrity.

### Don't:
- **Don't use pure #000000:** It kills the "Obsidian" depth. Stick to `surface_container_lowest` (#0e0e0e).
- **Don't use standard icons:** Use "Thin" or "Light" weight stroke icons (1px or 1.5px) to match the Inter typography weight.
- **Don't use traditional "Success Green":** Use the `outline` or `tertiary` tokens to keep the palette sophisticated and "Modern Family" specific.