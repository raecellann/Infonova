import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import infonovaLogo from "../../assets/images/infonova-logo.png";
import cnnLogo from "../../assets/images/cnn-logo.png";
import gmaLogo from "../../assets/images/gma-logo.png";
import inqLogo from "../../assets/images/inq-logo.png";
import mbLogo from "../../assets/images/mb-logo.png";
import rapplerLogo from "../../assets/images/rappler-logo.png";
import backgroundImage from "../../assets/images/background.jpg";

import { useSearch } from "../../context/searchContext";

export default function Home() {
  const [searchQuery, setSearchQuery] = useState("");
  const [suggestionValue, setSuggestionValue] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const navigate = useNavigate();
  const searchBoxRef = useRef(null);
  
  const { 
    search, 
    results = [], 
    loading, 
    suggestions, 
    showSuggestions, 
    setQuery, 
    selectSuggestion, 
    setShowSuggestions 
  } = useSearch();

  // Lock scroll when on search screen
  useEffect(() => {
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "auto";
      document.documentElement.style.overflow = "auto";
    };
  }, []);

  // Hide suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [setShowSuggestions]);

  // Navigate automatically if results exist
  useEffect(() => {
    if (results?.[0]) {
      navigate("/result");
    }
  }, [results, navigate]);

  // Handle search submission
  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    search(searchQuery);
    navigate("/result");
  };

  // Handle typing (and trigger suggestions via context)
  const handleInputChange = (e) => {
    const value = e.target.value;
    setSearchQuery(value);
    setSuggestionValue("");
    setHighlightedIndex(-1);
    setShowSuggestions(false);
    
    // Use context to handle suggestions
    setQuery(value);
  };

  // Keyboard navigation for suggestion list
  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => {
        const newIndex = prev < suggestions.length - 1 ? prev + 1 : 0;
        const base = searchQuery.endsWith(" ") ? searchQuery : searchQuery + " ";
        setSuggestionValue(`${base}${suggestions[newIndex]}`);
        return newIndex;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => {
        const newIndex = prev > 0 ? prev - 1 : suggestions.length - 1;
        const base = searchQuery.endsWith(" ") ? searchQuery : searchQuery + " ";
        setSuggestionValue(`${base}${suggestions[newIndex]}`);
        return newIndex;
      });
    } else if (e.key === "Enter" && highlightedIndex >= 0) {
      e.preventDefault();
      const selectedSuggestion = suggestions[highlightedIndex];
      handleSuggestionSelect(selectedSuggestion);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion) => {
    const base = searchQuery.endsWith(" ") ? searchQuery : searchQuery + " ";
    const fullQuery = `${base}${suggestion}`;
    setSearchQuery(fullQuery);
    setSuggestionValue("");
    setShowSuggestions(false);
    setHighlightedIndex(-1);
    
    // Use context to handle the selection
    selectSuggestion(suggestion);
  };

  // Click suggestion
  const handleSuggestionClick = (suggestion) => {
    handleSuggestionSelect(suggestion);
  };

  const glassStyle = {
    background: "rgba(255, 255, 255, 0.14)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.3)",
    boxShadow:
      "0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.5), inset 0 -1px 0 rgba(255, 255, 255, 0.1), inset 0 0 14px 7px rgba(255, 255, 255, 0.05)",
  };

  return (
    <div className="h-screen w-screen relative overflow-hidden">
      {/* Background */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      />
      <div className="absolute inset-0 bg-black opacity-40"></div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-screen w-screen py-8">
        {/* Header */}
        <div className="w-full mb-7">
          <div className="bg-white w-screen relative py-6 flex items-center justify-center shadow-lg mx-[-50vw] left-[50%] right-[50%]">
            <div className="absolute top-0 left-0 right-0 h-1 bg-black"></div>
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-black"></div>
            <div className="absolute top-2 left-0 right-0 h-1 bg-black"></div>
            <div className="absolute bottom-2 left-0 right-0 h-1 bg-black"></div>
            <img
              src={infonovaLogo}
              alt="Infonova"
              className="h-16 object-contain relative z-10"
            />
          </div>
          <p className="text-xl text-white drop-shadow-md text-center mt-6 px-2">
            Your Gateway to News and Information
          </p>
        </div>

        {/* Search Section */}
        <div className="w-full max-w-2xl mb-14" ref={searchBoxRef}>
          <form onSubmit={handleSearch} className="relative">
            <div className="relative">
              <input
                type="text"
                style={glassStyle}
                value={suggestionValue || searchQuery}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Search Article"
                className="w-full px-4 py-4 text-lg text-white placeholder-white rounded-full border-2 border-white focus:outline-none focus:ring-4 focus:ring-blue-300 shadow-lg font-inter font-bold"
              />
              <button
                type="submit"
                disabled={loading}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-2 rounded-full transition-colors duration-200"
              >
                {loading ? (
                  <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                )}
              </button>
            </div>

            {/* Suggestions */}
            {showSuggestions && suggestions.length > 0 && (
              <div
                style={{
                  ...glassStyle,
                  background: "rgba(255, 255, 255, 0.95)",
                }}
                className="absolute w-full mt-2 rounded-lg shadow-xl overflow-hidden z-50"
              >
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className={`px-4 py-3 hover:bg-blue-100 cursor-pointer text-gray-800 font-medium transition-colors duration-150 border-b border-gray-200 last:border-b-0 ${
                      highlightedIndex === index ? "bg-blue-100" : ""
                    }`}
                  >
                    {`${searchQuery.endsWith(" ") ? searchQuery : searchQuery + " "}${suggestion}`}
                  </div>
                ))}
              </div>
            )}
          </form>
        </div>

        {/* Supported Websites */}
        <div className="w-full max-w-4xl">
          <h2 className="text-2xl md:text-3xl font-bold text-white text-center mb-8 drop-shadow-lg">
            SUPPORTED WEBSITES
          </h2>

          <div className="flex justify-center">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-10 justify-items-center">
              {[
                { name: "GMA", logo: gmaLogo },
                { name: "CNN", logo: cnnLogo },
                { name: "Inquirer", logo: inqLogo },
                { name: "Manila Bulletin", logo: mbLogo },
                { name: "Rappler", logo: rapplerLogo },
              ].map((site, i) => (
                <div
                  key={i}
                  style={glassStyle}
                  onClick={() => {
                    setSearchQuery(site.name);
                    search(site.name);
                    navigate("/result");
                  }}
                  className="cursor-pointer p-4 flex items-center justify-center rounded-2xl transform transition-all duration-300 hover:-translate-y-2 hover:scale-105 hover:shadow-xl active:scale-95"
                >
                  <img
                    src={site.logo}
                    alt={`${site.name} Logo`}
                    className="w-16 h-12 object-contain"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-4 text-center">
          <p className="text-white text-sm drop-shadow-md">
            Powered by Infonova • Aggregating news from trusted sources
          </p>
        </div>
      </div>
    </div>
  );
}