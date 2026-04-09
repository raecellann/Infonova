// App.jsx
import { Routes, Route } from "react-router-dom";
import { SearchProvider } from "./context/searchContext";
import { ToastProvider } from "./context/ToastContext";
import Toast from "./components/Toast";
import Layout from "./Layouts/Default";
import Home from "./pages/home/HomePage";
// import Search from "./pages/search/search";
import Result from "./pages/result/result";

function App() {
  
  return (
    <ToastProvider>
      <SearchProvider>
        <Toast />
        <Routes>
        {/* Layout with nested routes */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          {/* <Route path="search" element={<Search />} /> */}
          <Route path="result" element={<Result />} />
          {/* <Route path="print-document" element={<Sample />} /> */}
        </Route>

        {/* Route without layout */}
        {/* <Route path="/login" element={<Login />} /> */}
        </Routes>
      </SearchProvider>
    </ToastProvider>
  );
}

export default App;
