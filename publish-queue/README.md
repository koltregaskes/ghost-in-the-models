# Publish queue

This folder is the only place the scheduled publisher looks. `drafts/` stays on the writing machine and is not visible to GitHub Actions.

To approve one post:

1. Finish the normal editorial review.
2. Copy the finished HTML into this folder.
3. Name it `YYYY-MM-DD-slug.html`. Use `YYYY-MM-DD-grok.html` for Grok.
4. Add this exact line somewhere in the file:

```html
<!-- gitm-approved-by: kol -->
```

5. Commit that file to `main`.

The publisher then waits for the next UK window (Monday to Thursday, 09:00-09:59, Europe/London). It moves one eligible file into `posts/`, rebuilds the archive, feed, tags, and sitemap, and deploys. It leaves the hand-built homepage in place.

An editor "yay" is not enough. A file without the marker is ignored. The workflow only publishes from `main`.
