# consolidate-src-structure

## Motivations and Context

- `src/` spreads eleven files across six top-level directories. Every directory
  holds one to three files. The grouping costs more to read than it explains.

- A post is three files in three unrelated places: `src/posts/Don't Use
  Lodash.md`, `src/assets/titles/dont-use-lodash.svg`, and the route that binds
  them. Nothing on disk says they belong together. The only link is the
  `titleSvg` frontmatter field, matched by name at build time.

- `src/posts/` is not where Astro looks for content. The convention for a glob
  collection is `src/content/`. The current name works, but it teaches the wrong
  habit and hides the directory's role.

- The post's frontmatter carries `id: Don't Use Lodash`, which does nothing. It
  is absent from the schema, and the glob loader honours only `slug`, never `id`
  (`node_modules/astro/dist/content/loaders/glob.js:12`). The URL comes from the
  filename alone. A dead field in the one post is a template for every post
  after it.

- `titleSvg` is configuration standing in for a convention. Once the drawing
  lives beside the post there is exactly one place it can be, and the field is
  restating the directory listing.

- Published URLs are frozen. `/posts/dont-use-lodash` must resolve after the
  move. This is a hard constraint, not a preference.

## Outcomes

- `src/` holds three directories and two files:

  ```
  src/
    content.config.ts
    styles.css
    content/posts/dont-use-lodash/
      index.md
      title.svg
    components/
      Base.astro
      Comments.astro
      PostTitle.astro
    pages/
      index.astro
      posts/[...slug].astro
  ```

  `content.config.ts` sits at the `src/` root because Astro requires it there.

- Every post is a directory, `content/posts/<slug>/index.md`, whether or not it
  has assets. One rule, no per-post decision, and a post can gain a drawing
  later without moving. The directory name is the URL.

- `/posts/dont-use-lodash` is unchanged. The glob loader slugifies each path
  segment and then strips a trailing `/index`
  (`node_modules/astro/dist/content/utils.js:277`), so
  `dont-use-lodash/index.md` and `Don't Use Lodash.md` produce the same slug.
  Verified in the installed Astro source, not assumed.

- A post's drawing is `title.svg` beside its `index.md`, found by convention.
  `titleSvg` is gone from the frontmatter and from the schema, which reduces to
  `{ title: z.string() }`. The dead `id` field goes with it.

- `DrawnTitle.astro` becomes `PostTitle.astro` and takes the post, not a name
  and a label. It renders the drawing when `title.svg` is there and a plain
  `<h1>{post.data.title}</h1>` when it is not. A missing drawing stops being an
  error, so the component no longer throws.

- Every post now renders a heading. Today `[...slug].astro:20` gates the whole
  title on `titleSvg`, so a post without a drawing renders no `<h1>` at all.
  This is a deliberate behaviour change, not a side effect.

- `tokens.css` and `editorial.css` merge into one `src/styles.css`. The two
  files currently document each other — "the only file you need to touch to
  restyle the site", "change the palette there, not here" — and that wording
  cannot survive the merge. The merged file opens with the token block under a
  section heading, and the header comments point at the section instead of a
  filename. Losing the one-file-to-restyle affordance is the accepted price of
  dropping `src/styles/`.

- References to moved files are corrected wherever they live, including the two
  outside `src/`: the comment in `astro.config.mjs:11` naming
  `src/styles/editorial.css`, and the usage example in `scripts/rm-to-title.py:20`
  naming `src/assets/titles/`. Nothing else outside `src/` is touched. Finishing
  a move means leaving no stale path behind; this is not a licence to reorganise
  the repository root.

- `src/layouts/`, `src/styles/`, `src/assets/`, and `src/posts/` no longer
  exist. `Base.astro` moves into `components/`, which is against Astro's own
  layout/component split; with three files the extra directory bought less than
  it cost.

- Total directory count does not fall. Six before, six after — the nesting moved
  from `src/` into `content/posts/<slug>/`. The gain is one obvious home per
  concern and a post that is a single directory, not a smaller tree. Anyone
  measuring this branch by directory count will conclude it did nothing.

- Known constraint the new layout introduces: `PostTitle` resolves its drawing
  at `content/posts/${post.id}/title.svg`, so `post.id` must equal the directory
  name. Setting `slug:` in a post's frontmatter breaks that equality, and the
  drawing silently falls back to a plain heading rather than failing. Posts take
  their URL from the directory name. Do not add `slug:`.

## Scope

- src/content.config.ts
  - Point the glob loader base at `./src/content/posts`.
  - Reduce the schema to `{ title: z.string() }`.
    - Drop `titleSvg`.
- src/content/posts/dont-use-lodash/index.md
  - Move here from `src/posts/Don't Use Lodash.md`.
  - Delete the `id` and `titleSvg` frontmatter fields.
    - Leave `title: Don't Use Lodash (anymore)` as the only field.
- src/content/posts/dont-use-lodash/title.svg
  - Move here from `src/assets/titles/dont-use-lodash.svg`.
  - Rename its root class `drawn-title-ink` to `post-title-ink`.
- src/components/PostTitle.astro
  - Move here from `src/components/DrawnTitle.astro`.
  - Replace the `name` and `label` props with a single `post` prop.
  - Glob `../content/posts/*/title.svg` as raw strings.
    - Look up `../content/posts/${post.id}/title.svg`.
  - Render the SVG in an `<h1 class="post-title">` when one is found.
    - Label it with `post.data.title`.
  - Render `<h1>{post.data.title}</h1>` when none is found.
  - Remove the `throw` on a missing drawing.
- src/components/Base.astro
  - Move here from `src/layouts/Base.astro`.
  - Import `../styles.css`.
- src/pages/posts/[...slug].astro
  - Import `Base` from `../../components/Base.astro`.
  - Import `PostTitle` from `../../components/PostTitle.astro`.
  - Render `<PostTitle post={post} />` unconditionally.
    - Remove the `post.data.titleSvg &&` guard.
- src/pages/index.astro
  - Import `Base` from `../components/Base.astro`.
- src/styles.css
  - Merge `src/styles/tokens.css` and `src/styles/editorial.css` here.
    - Tokens first, under a section heading, then the element styles.
    - Drop the `@import "./tokens.css";` line.
  - Rewrite both header comments to name the token section, not a file.
    - Remove "the only file you need to touch to restyle the site".
    - Remove "change the palette there, not here".
  - Rename `.drawn-title` to `.post-title`.
  - Rename `.drawn-title-ink` to `.post-title-ink`.
  - Rename the `drawn-title-stroke` keyframes to `post-title-stroke`.
- astro.config.mjs
  - Change the comment path `src/styles/editorial.css` to `src/styles.css`.
- scripts/rm-to-title.py
  - Emit `class="post-title-ink"` instead of `class="drawn-title-ink"`.
  - Change the usage example output path.
    - To `src/content/posts/my-post/title.svg`.
- Deleted directories
  - `src/posts/`, `src/assets/`, `src/layouts/`, `src/styles/`.

## Out of scope

- No change to any published URL.
- No new posts, and no content edits inside the post body.
- No change to `src/components/Comments.astro`.
- No visual change beyond posts without a drawing gaining an `<h1>`.
- No change to `README.md`, `package.json`, `tsconfig.json`, or
  `wrangler.jsonc`.
- No rewrite of `scripts/rm-to-title.py` beyond the two string changes.
- No `slug:` frontmatter field on any post, now or later.

## Verification steps

- `npm run check` passes with no errors.
- `npm run build` succeeds.
- `dist/posts/dont-use-lodash.html` exists.
- That page contains an inline `<svg>` inside `<h1 class="post-title">`.
  - With `aria-label="Don't Use Lodash (anymore)"`.
- `dist/index.html` links to `/posts/dont-use-lodash`.
- Temporarily renaming `title.svg` builds a plain `<h1>` and does not throw.
- Grepping `src`, `scripts`, and `astro.config.mjs` for `src/styles`,
  `src/assets`, `src/posts`, and `src/layouts` returns nothing.
- `grep -rn "drawn-title\|titleSvg\|DrawnTitle" src scripts` returns nothing.
- `npm run dev` renders the post with the stroke animation intact.
