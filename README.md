This demonstrates how to reproduce a bug in traefik that cause common web browsers to successfully save a
truncated download.

To run it:

```
$ docker compose up
```

Go to the URL https://localhost:16243/ to get started. There is various download links but any of them will
trigger the problem. The shorter downloads tend to fail without delay and the other ones take a while but
eventually the result is always the same: The download is successful, but we have a truncated file on disk.

There is also various other configurations of reverse proxies, the most interesting one is the one where
nginx fronts traefik: The bug does not pass through nginx because it seems to check the `Content-Length`
header or something like that.
