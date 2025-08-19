# SAINTS Lab Website (GitHub Pages)

This is a lightweight Jekyll site for **SAINTS Lab**. It is static, fast, and easy to maintain.

## Deploy
1. Create a GitHub repository named `saintslab.github.io` under your `saintslab` account or org.
2. Upload these files to the repo root and push to the `main` branch.
3. GitHub Pages will publish automatically at https://saintslab.github.io.

## Content
- Add, edit, or remove people under `_people/`. The filename becomes the URL slug.
  Example:
  ```markdown
  ---
  name: Jane Doe
  role: Postdoc
  email: jane@saintslab.org
  photo: /assets/img/jane.jpg
  website: https://janedoe.example
  ---

  Short bio paragraph with research interests, awards, and links.
  ```
- Manage publications in `_data/publications.json` with fields:
  `title`, `authors` (list), `venue`, `year` (string), optional `link`, optional `resources` (list of `{label,url}`).
- Manage projects in `_data/projects.yml` with `title`, `summary`, optional `link`, optional `tags`.
- Images go in `assets/img/`.

## Local preview (optional)
If you have Ruby and Bundler, run `bundle exec jekyll serve` to preview locally.
