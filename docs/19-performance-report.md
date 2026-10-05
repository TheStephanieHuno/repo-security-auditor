# `next dev` performance report

Measured locally on Windows with a fresh `.next` directory and sequential HTTP requests to each route. First-visit figures include route compilation; second-visit figures are warm-route responses.

| Route | Before: compile | Before: first response | Before: second response | After: compile | After: first response | After: second response |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `/dashboard` | 4.8 s | 5.324 s | 100 ms | 7.1 s | 8.247 s | 219 ms |
| `/repositories` | 2.0 s | 2.443 s | 47 ms | 1.354 s | 1.663 s | 154 ms |

Before used the previous `next dev` configuration with the server-side dev `splitChunks` override. After uses `next dev --turbopack`, with the custom webpack override removed and `optimizePackageImports: ["lucide-react"]` enabled. Turbopack was kept: no incompatible custom webpack configuration, loader, or plugin was found. The dashboard cold compile was slower in this single local sample; repositories improved. Measurements are environment-dependent.
