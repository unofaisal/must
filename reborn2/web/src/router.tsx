import { createHashHistory, createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { History } from "./components/History";
import { Home } from "./components/Home";
import { Pipeline } from "./components/Pipeline";
import { Review } from "./components/Review";
import { Shell } from "./components/Shell";

const rootRoute = createRootRoute({ component: Shell });
const route = <P extends string>(path: P, component: () => React.JSX.Element) =>
  createRoute({ getParentRoute: () => rootRoute, path, component });

// Hash history (#/review) so a refresh works when FastAPI serves the built files.
export const router = createRouter({
  routeTree: rootRoute.addChildren([
    route("/", Home),
    route("/review", Review),
    route("/pipeline", Pipeline),
    route("/history", History),
  ]),
  history: createHashHistory(),
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
