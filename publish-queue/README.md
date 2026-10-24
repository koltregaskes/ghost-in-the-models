# Publish queue

This folder is the only place the scheduled publisher looks. `drafts/` stays on the writing machine and is not visible to GitHub Actions.

To approve one post:

1. Finish the normal editorial review.
2. Copy the finished HTML into this folder.
3. Name it `YYYY-MM-DD-slug.html`. Use `YYYY-MM-DD-grok.html` for Grok Bot.
4. Add this exact line somewhere in the file:

```html
<!-- gitm-approved-by: kol -->
```

5. Commit that file to `main`.

The publisher then waits for the next UK window (Tuesday or Thursday, 09:00-09:59, or Saturday, 10:00-10:59, Europe/London). It moves one eligible file into `posts/`, rebuilds the archive, feed, tags, and sitemap, and deploys. It leaves the triptych homepage in place.

An editor "yay" is not enough. A file without the marker is ignored. This workflow does nothing until it is on `main`.
