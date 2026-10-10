# outline.yml Schema Reference

The `outline.yml` file defines the book's table of contents structure and chapter specifications. This file guides the AI content generation process and determines the book's organization.

## Structure Overview

```yaml
book:
  # Book-level metadata

chapters:
  # Array of chapter specifications
```

## Book Section

| Field           | Type    | Required | Description                                        |
| --------------- | ------- | -------- | -------------------------------------------------- |
| `title`         | string  | Yes      | Book title (should match cc-config.yml)            |
| `subtitle`      | string  | No       | Book subtitle (conditional)                        |
| `description`   | string  | Yes      | Book concept/description for AI generation         |
| `target_length` | integer | Yes      | Target word count for entire book (default: 40000) |

### Recommended Word Counts

| Book Type           | Target Length   | Approximate Pages |
| ------------------- | --------------- | ----------------- |
| Novella             | 20,000 - 40,000 | 75 - 150          |
| Standard Book       | 40,000 - 60,000 | 150 - 225         |
| Comprehensive Guide | 60,000 - 80,000 | 225 - 300         |

## Chapters Array

Each chapter object contains:

| Field                 | Type           | Required | Description                                               |
| --------------------- | -------------- | -------- | --------------------------------------------------------- |
| `number`              | integer        | Yes      | Sequential chapter number (1, 2, 3...)                    |
| `chapter_title`       | string         | Yes      | Chapter title WITHOUT "Chapter N:" prefix                 |
| `chapter_description` | string         | Yes      | 3-5 sentence detailed description of chapter scope        |
| `sections`            | array of beats | Yes      | 3-8 section beats — the chapter's spine (see below)       |
| `estimated_pages`     | string         | Yes      | Page range estimate (e.g., "6-8")                         |
| `status`              | string         | Yes      | Generation status: `pending`, `generated`, or `edited`    |
| `custom_prompt`       | string         | No       | Optional custom prompt override (usually empty initially) |

### Section Beat Fields

Each entry in a chapter's `sections` array is a **section beat** — one section that
will actually be written. A beat carries:

| Field         | Type             | Required | Description                                                                |
| ------------- | ---------------- | -------- | -------------------------------------------------------------------------- |
| `heading`     | string           | Yes      | The section's working title (concise, specific — not "Intro")              |
| `summary`     | string           | No       | 1-2 sentences naming exactly what the section covers                       |
| `key_points`  | array of strings | No       | 2-5 must-hit bullets — concrete claims, examples, data, or steps           |
| `word_target` | integer          | No       | This section's share of the chapter's words (beats sum to ~chapter target) |

### Chapter Title Guidelines

- **DO**: Use descriptive, engaging titles
- **DON'T**: Include "Chapter N:" prefix (added automatically by templates)
- **Good**: `"The Foundations of Machine Learning"`
- **Bad**: `"Chapter 1: The Foundations of Machine Learning"`

### Chapter Description Guidelines

The `chapter_description` should:

- Be 3-5 sentences long
- Explain what the chapter covers and why it's important
- Describe how it connects to adjacent chapters
- Highlight what makes this chapter unique or essential

**Example**:

```yaml
chapter_description: |
  This chapter explores the fundamental concepts of machine learning, establishing the theoretical
  foundation for the techniques covered in later chapters. We examine supervised and unsupervised
  learning paradigms, introducing key terminology and mathematical frameworks. The chapter bridges
  basic statistics (covered in Chapter 1) with practical algorithms (introduced in Chapter 3),
  providing the conceptual scaffolding needed to understand modern ML systems.
```

### Section Beats Guidelines

The `sections` list (built in pass 2 of outline generation) should:

- Contain **3-8 beats** — one per section that will actually be written (coarser
  and richer than a long flat list of subtopics)
- Cover the full scope of the chapter with no internal overlap, ordered so the
  chapter builds logically from opening to close
- Stay in the chapter's lane — no overlap with sibling chapters
- Give each beat a `summary` and `key_points` so the writer never has to invent
  structure or pad with filler
- Weight `word_target` by how much each section deserves; the targets should sum
  to roughly the chapter's word budget

**Example**:

```yaml
sections:
  - heading: "Machine learning vs. traditional programming"
    summary: "Frame ML as learning rules from data, contrasted with hand-coded logic."
    key_points:
      - "Rules-from-data vs. rules-by-hand, with one worked contrast"
      - "When ML is the wrong tool"
    word_target: 700
  - heading: "The core learning paradigms"
    summary: "Walk through supervised, unsupervised, and reinforcement learning."
    key_points:
      - "Classification vs. regression under supervision"
      - "Clustering and dimensionality reduction without labels"
      - "Reward-driven reinforcement learning"
    word_target: 1100
  - heading: "Data, evaluation, and the bias-variance tradeoff"
    summary: "Cover train/test/validation splits and how overfitting is measured."
    key_points:
      - "Why a held-out test set matters"
      - "Overfitting vs. underfitting, with cross-validation"
    word_target: 900
  - heading: "Pitfalls and best practices"
    summary: "Close with the mistakes beginners make and how to avoid them."
    key_points:
      - "Leakage, imbalanced data, premature optimization"
    word_target: 600
```

### Status Values

| Status      | Meaning                                    |
| ----------- | ------------------------------------------ |
| `pending`   | Chapter not yet generated                  |
| `generated` | Chapter content created by AI              |
| `edited`    | Chapter manually reviewed/edited by author |

## Complete Example

```yaml
book:
  title: "The Ultimate Guide to Chengdu Cuisine"
  subtitle: "A Journey Through Sichuan's Most Beloved Dishes"
  description: |
    A comprehensive guide to Chengdu cuisine, exploring the history, ingredients, and techniques
    behind Sichuan's most iconic dishes. From hotpot to dan dan noodles, this book celebrates
    the bold flavors and rich culinary traditions of China's "City of Gastronomy."
  target_length: 40000

chapters:
  - number: 1
    chapter_title: "The Culinary Heritage of Chengdu"
    chapter_description: |
      This chapter traces the historical evolution of Chengdu cuisine from ancient times through
      its UNESCO designation as a City of Gastronomy. We explore the geographic, cultural, and
      agricultural factors that shaped Sichuan cooking, establishing context for the dishes and
      techniques covered in subsequent chapters.
    sections:
      - heading: "Geography and the roots of a cuisine"
        summary: "How Chengdu's basin geography and agricultural abundance shaped its food."
        key_points:
          - "The Sichuan basin's climate and produce"
          - "Trade routes that brought in chili and exchange"
        word_target: 900
      - heading: "Religion, court, and folk traditions"
        summary: "The cultural forces — Buddhism, Taoism, imperial vs. folk cooking — behind the table."
        key_points:
          - "Buddhist/Taoist influence on ingredients and restraint"
          - "Imperial cuisine vs. everyday folk traditions"
        word_target: 800
      - heading: "The má-là flavor profile emerges"
        summary: "Trace how the signature numbing-and-spicy profile developed over time."
        key_points:
          - "Arrival of the chili and its fusion with Sichuan peppercorn"
        word_target: 700
      - heading: "Modern Chengdu: UNESCO and the street"
        summary: "From the City of Gastronomy designation to today's teahouse and street-food scene."
        key_points:
          - "UNESCO City of Gastronomy designation"
          - "Teahouse culture and street-food traditions"
        word_target: 800
    estimated_pages: "6-8"
    status: "pending"
    custom_prompt: ""

  - number: 2
    chapter_title: "Essential Ingredients and Flavors"
    chapter_description: |
      Building on the historical foundation, this chapter introduces the core ingredients that
      define Sichuan cuisine. We examine Sichuan peppercorns, chili peppers, doubanjiang, and
      other essential components, explaining their unique characteristics and how they create
      the complex layers of flavor that make Chengdu food distinctive.
    sections:
      - heading: "The two pillars: peppercorn and chili"
        summary: "Sichuan peppercorns (má) and chili peppers — varieties, heat, and flavor."
        key_points:
          - "Peppercorn varieties and the numbing sensation"
          - "Chili heat levels and flavor profiles"
        word_target: 1000
      - heading: "Fermented depth: doubanjiang and friends"
        summary: "How fermented pastes and aromatics build the cuisine's umami base."
        key_points:
          - "Doubanjiang fermentation and umami"
          - "Ginger, garlic, scallions, and Sichuan pickles"
        word_target: 900
      - heading: "The seven tastes and supporting players"
        summary: "The taste framework plus vinegars, sesame, and seasonal vegetables."
        key_points:
          - "The seven basic tastes of Sichuan cuisine"
          - "Vinegars and sesame paste/oil applications"
        word_target: 900
      - heading: "Building a pantry outside China"
        summary: "Sourcing, quality assessment, and an essential-vs-optional shopping list."
        key_points:
          - "Quality assessment and sourcing substitutions"
          - "Essential vs. optional pantry items"
        word_target: 700
    estimated_pages: "7-9"
    status: "pending"
    custom_prompt: ""

  - number: 3
    chapter_title: "Fundamental Cooking Techniques"
    chapter_description: |
      This chapter bridges ingredients and finished dishes by teaching the core cooking techniques
      used throughout Chengdu cuisine. From stir-frying and braising to the art of making chili oil,
      readers learn the skills needed to execute the recipes in later chapters with confidence and
      authenticity.
    sections:
      - heading: "Mastering the wok"
        summary: "High-heat stir-frying and dry-frying — the foundational wok skills."
        key_points:
          - "Bào (high-heat stir-frying) technique and heat control"
          - "Gān biān (dry-frying) for texture"
        word_target: 1100
      - heading: "Braising, frying, and steaming"
        summary: "Red braising, deep-frying, and steaming — when and how to use each."
        key_points:
          - "Hóngshāo red braising and variations"
          - "Deep-frying oil temperature and double-frying"
          - "Steaming equipment and timing"
        word_target: 1000
      - heading: "Chili oil and cold-mixing"
        summary: "Making chili oil and the cold-mixing technique for preserved vegetables."
        key_points:
          - "Chili oil: temperatures and aromatics"
          - "Liángbàn cold-mixing basics"
        word_target: 800
      - heading: "Balancing flavor and troubleshooting"
        summary: "Tying it together: balancing má-là and fixing common mistakes."
        key_points:
          - "Balancing numbing and spicy in a finished dish"
          - "Common mistakes and how to recover"
        word_target: 700
    estimated_pages: "8-10"
    status: "pending"
    custom_prompt: ""

  - number: 4
    chapter_title: "Hotpot: The Heart of Chengdu Dining"
    chapter_description: |
      Devoted entirely to Chengdu's most famous dish, this chapter explores hotpot in depth.
      We cover broth preparation, ingredient selection, dipping sauce customization, and the
      social rituals that make hotpot central to Chengdu's food culture. This chapter demonstrates
      how all previous concepts (history, ingredients, techniques) combine in one iconic dish.
    sections:
      - heading: "From river workers to restaurants"
        summary: "The origin story of Chengdu hotpot and how it became central to dining."
        key_points:
          - "Humble dockworker origins"
          - "Rise into restaurant culture"
        word_target: 700
      - heading: "Anatomy of the pot and the broth"
        summary: "Pot configurations and building a balanced má-là base."
        key_points:
          - "Pot types and split-pot configurations"
          - "Beef tallow base, aromatics, and balancing má and là"
        word_target: 1100
      - heading: "Ingredients and the dipping station"
        summary: "What goes in the pot — from staples to adventurous cuts — and the sauce bar."
        key_points:
          - "Essential meats, vegetables, and fungi"
          - "Special ingredients (duck blood, tripe) and the dipping-sauce station"
        word_target: 1000
      - heading: "Etiquette, setup, and regional styles"
        summary: "Cooking order and etiquette, home vs. restaurant setup, and regional contrasts."
        key_points:
          - "Eating etiquette and cooking order"
          - "Chongqing vs. Chengdu styles"
        word_target: 800
    estimated_pages: "8-10"
    status: "pending"
    custom_prompt: ""

  # Additional chapters would follow...
```

## Word Distribution

The book's `target_length` is divided across chapters, then across each chapter's
section beats:

```python
words_per_chapter = target_length // len(chapters)
```

Within a chapter, each beat's `word_target` is its share of `words_per_chapter`.
Beats with an explicit `word_target` keep it; any remaining words are split evenly
across the unweighted beats (an all-even split if none are weighted). The beats'
targets should sum to roughly `words_per_chapter`.

**Example**: a 40,000-word book with 8 chapters = ~5,000 words per chapter; a
chapter with 4 beats might weight them 1500 / 1500 / 1100 / 900.

## Usage in Content Generation

1. **Outline Generation (Phase 3)**: Claude creates this file in two passes — a
   chapter list (`outline-prompt.jinja2`), then section beats per chapter
   (`outline-sections.jinja2`)
2. **Chapter Generation (Phase 4)**: each chapter's `sections` beats become the
   section spine; the writer drafts one section per beat
3. **Prompt Rendering**: `sections` populates `chapter-generation/system.jinja2`,
   and each beat populates `chapter-generation/section.jinja2`
   (`section_heading` / `section_summary` / `section_key_points` /
   `section_word_target`)
4. **Quality Control**: user reviews and can edit the section beats before generation

## Validation Rules

The validation script checks:

- ✅ `book` section exists with required fields
- ✅ `chapters` array exists and has at least 1 chapter
- ✅ Chapter numbers are sequential (1, 2, 3...)
- ✅ Each chapter has `chapter_title`, `chapter_description`, `sections`
- ✅ `sections` has at least 1 beat (recommend 3-8), each with a `heading`
- ⚠️ Warns if chapters have vastly different `estimated_pages`
