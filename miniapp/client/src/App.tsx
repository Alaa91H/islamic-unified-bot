/** تصميم «محراب اليوم»: مساحة تطبيق واحدة لتجربة Telegram سريعة ومركزة. */
import Home from "@/pages/Home";
import ErrorBoundary from "./components/ErrorBoundary";

export default function App() {
  return (
    <ErrorBoundary>
      <Home />
    </ErrorBoundary>
  );
}
