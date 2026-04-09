import React, { useState } from "react";
import { Menu, X } from "lucide-react";
import { Link } from "react-router-dom";

const NavigationComponents = () => {
  const [isOpen, setIsOpen] = useState(false);
  const toggleSidebar = () => setIsOpen(!isOpen);

  return (
    <div className="print:hidden">
      {/* Toggle Button */}
      <div className="p-4">
        <button
          onClick={toggleSidebar}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 shadow-sm text-black rounded-md hover:bg-blue-600 hover:text-white transition duration-200"
        >
          <Menu className="w-5 h-5" />
          <span className="font-medium">Menu</span>
        </button>
      </div>

      {/* Backdrop */}
      {isOpen && (
        <div
          onClick={toggleSidebar}
          className="fixed inset-0 bg-black bg-opacity-40 backdrop-blur-sm z-40 transition-opacity"
        />
      )}

      {/* Sidebar */}
      <nav
        className={`fixed top-0 left-0 h-full bg-white shadow-lg border-gray-200 transform transition-transform duration-300 z-50 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ width: "240px" }}
        aria-label="Sidebar Navigation"
      >
        <div className="h-full flex flex-col py-6 px-6">
          <div className="flex justify-end">
            <button
              onClick={toggleSidebar}
              className="p-2 bg-gray-100 hover:bg-red-600 transition-colors duration-200 text-gray-600 hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-300"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <ul className="flex flex-col gap-6 text-left mt-12">
            <li>
              <Link
                to="/"
                onClick={toggleSidebar}
                className="block hover:animate-pulse text-gray-800 hover:text-blue-600 transition-colors font-medium"
              >
                🏠 Home
              </Link>
            </li>
            <li>
              <Link
                to="/DAR"
                onClick={toggleSidebar}
                className="block hover:animate-pulse text-gray-800 hover:text-blue-600 transition-colors font-medium"
              >
                📋 DAR
              </Link>
            </li>
            <li>
              <Link
                to="/ATTENDANCE"
                onClick={toggleSidebar}
                className="block hover:animate-pulse text-gray-800 hover:text-blue-600 transition-colors font-medium"
              >
                🕒 Attendance
              </Link>
            </li>
            <li>
              <Link
                to="/ACCOUNT"
                onClick={toggleSidebar}
                className="block hover:animate-pulse text-gray-800 hover:text-blue-600 transition-colors font-medium"
              >
                👤 Account
              </Link>
            </li>
          </ul>

          <div className="mt-auto pt-10 text-sm text-gray-400 animate-pulse">
            &copy; {new Date().getFullYear()} MyApp
          </div>
        </div>
      </nav>
    </div>
  );
};

export default NavigationComponents;
