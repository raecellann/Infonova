import React, { useState, useEffect, useRef } from "react";

// Temporary static images (for now)
// Add the backend for scraping later
import firstArticleImage from "../../assets/images/article-photos/image-5.png";
import secondArticleImage from "../../assets/images/article-photos/image-4.png";
import thirdArticleImage from "../../assets/images/article-photos/image-3.png";

import { useSearch } from "../../context/searchContext";
import { Link, useNavigate } from "react-router-dom";

export default function Result() {
  const { 
    search, 
    results = [], 
    loading, 
    loadingMore,
    hasMore,
    loadMore,
    suggestions, 
    showSuggestions, 
    setQuery, 
    selectSuggestion, 
    setShowSuggestions,
    query: contextQuery 
  } = useSearch();
  
  const navigator = useNavigate();

  const [suggestionValue, setSuggestionValue] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const searchBoxRef = useRef(null);

  const handleSearch = (e) => {
    e.preventDefault(); // prevent page reload
    setShowSuggestions(false);
    search(contextQuery);
  };

  // Handle typing (and trigger suggestions via context)
  const handleInputChange = (e) => {
    const value = e.target.value;
    setSuggestionValue("");
    setHighlightedIndex(-1);
    setShowSuggestions(false);
    
    // Use context to handle suggestions
    setQuery(value);
  };

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

  // Keyboard navigation for suggestion list
  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => {
        const newIndex = prev < suggestions.length - 1 ? prev + 1 : 0;
        const base = contextQuery.endsWith(" ") ? contextQuery : contextQuery + " ";
        setSuggestionValue(`${base}${suggestions[newIndex]}`);
        return newIndex;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => {
        const newIndex = prev > 0 ? prev - 1 : suggestions.length - 1;
        const base = contextQuery.endsWith(" ") ? contextQuery : contextQuery + " ";
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
    const base = contextQuery.endsWith(" ") ? contextQuery : contextQuery + " ";
    const fullQuery = `${base}${suggestion}`;
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

  const suggestionGlassStyle = {
    background: "rgba(255, 255, 255, 0.95)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.3)",
    boxShadow: "0 8px 32px rgba(0, 0, 0, 0.1)",
  };

  const sortedResults = [...results].sort((a, b) => a.rank - b.rank);

  const mainArticles = sortedResults.slice(0, 2);
  const sideArticles = sortedResults.slice(2);

  const placeholderImages = [firstArticleImage, secondArticleImage, thirdArticleImage];

  useEffect(() => {
    if (results.length === 0 && !loading) {
      navigator('/');
    }
  }, [results, loading, navigator]);

  return (
    <div className="min-h-screen w-screen bg-white">
      {/* Header */}
      <header className="flex items-center justify-between bg-[#00559B] px-6 py-4">
        <h1 className="text-2xl font-bold text-white">Infonova</h1>
        {/* <Link to="/" className="text-2xl font-bold text-white hover:underline focus:outline-none">
          Infonova
        </Link> */}
        {/* Search Form with Auto-suggest */}
        <form 
          onSubmit={handleSearch} 
          className="w-1/3 relative"
          ref={searchBoxRef}
        >
          <div className="relative">
            <input
              type="text"
              value={suggestionValue || contextQuery}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              style={glassStyle}
              placeholder="Search any news"
              className="w-full rounded-full px-4 py-2 text-sm focus:outline-none border border-gray-300 text-white placeholder-white"
            />
            
            {/* Search Button */}
            <button
              type="submit"
              className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white p-1 rounded-full transition-colors duration-200"
            >
              <svg
                className="w-4 h-4"
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
            </button>
          </div>

          {/* Suggestions Dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div
              style={suggestionGlassStyle}
              className="absolute w-full mt-2 rounded-lg shadow-xl overflow-hidden z-50 max-h-60 overflow-y-auto"
            >
              {suggestions.map((suggestion, index) => (
                <div
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className={`px-4 py-3 hover:bg-blue-100 cursor-pointer text-gray-800 font-medium transition-colors duration-150 border-b border-gray-200 last:border-b-0 ${
                    highlightedIndex === index ? "bg-blue-100" : ""
                  }`}
                >
                  {`${contextQuery.endsWith(" ") ? contextQuery : contextQuery + " "}${suggestion}`}
                </div>
              ))}
            </div>
          )}
        </form>
      </header>

      {/* 🔴 No Results Alert */}
      {!loading && results.length === 0 && (
        <div className="w-full bg-red-50 border border-red-300 text-red-700 text-center py-3 font-medium">
          No results found for "<span className="font-semibold">{contextQuery}</span>"
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex justify-center items-center h-[80vh]">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="ml-3 text-lg text-gray-600">Loading results...</p>
        </div>
      ) : (
        <div className="px-6 py-8 flex flex-col lg:flex-row gap-8 items-stretch">
          {/* Left section (Top 2 Articles) */}
          <div className="lg:w-2/5 flex flex-col space-y-6">
            {mainArticles.length > 0 && (
              mainArticles.map((article, index) => (
              <a
              key={index}
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 text-sm hover:text-[#00559B] hover: transition-colors duration-300"
              >
                <div
                  key={index}
                  className="bg-white border rounded-lg shadow-md overflow-hidden flex-1 flex flex-col 
                            transform transition-all duration-300 ease-in-out hover:scale-[1.02] hover:shadow-xl cursor-pointer"
                >
                  <img
                    src={article.meta_image || placeholderImages[index % placeholderImages.length]}
                    alt={article.title}
                    className="w-full h-80 object-cover transition-all duration-300 ease-in-out hover:brightness-105"
                  />
                  <div className="p-4 flex flex-col justify-between flex-1">
                    <div>
                      <p className="text-sm font-bold text-[#00559B]">
                        {`${article.source.split('_DATASETS')[0]} NEWS`}
                      </p>
                      <p className="text-xs text-gray-500 mb-2 truncate">{article.url}</p>
                      <h3 className="text-lg font-bold">{article.title}</h3>
                      <p className="text-sm text-gray-700 mt-2 line-clamp-3">{article.content}</p>
                    </div>
                    <div className="flex justify-end mt-2">
                    </div>
                  </div>
                </div>
                </a>
              ))
            )}
          </div>

          {/* Right section (More Articles) */}
          <aside className="lg:w-3/5 flex flex-col">
            <h3 className="text-lg font-semibold mb-4">More Articles</h3>
            <div className="space-y-6 h-full">
              {sideArticles.map((article, index) => (
                <a
                  key={index}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block"
                  style={{ textDecoration: "none", color: "inherit" }}
                >
                  <div
                    key={index}
                    className="flex space-x-4 border-b pb-4 transform transition-all duration-300 ease-in-out 
                              hover:scale-[1.02] hover:bg-gray-50 rounded-lg p-2 cursor-pointer"
                  >
                    <img
                      src={article.meta_image || placeholderImages[(index + 2) % placeholderImages.length]}
                      alt={article.title}
                      className="w-32 h-20 object-cover rounded transition-all duration-300 hover:brightness-105"
                    />
                    <div className="flex-1 flex flex-col justify-between">
                      <div>
                        <p className="text-sm font-bold text-[#00559B]">
                          {`${article.source.split('_DATASETS')[0]} NEWS`}
                        </p>
                        <p className="text-xs text-gray-500 mb-1 truncate max-w-[600px]">{article.url}</p>
                      </div>
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-bold leading-tight line-clamp-1">
                          {article.title}
                        </h4>
                      </div>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </aside>
        </div>
      )}

      {/* Load More Button - Always at the bottom */}
      <div className="w-full py-8 flex justify-center">
        {/* <div className="text-xs text-gray-500 mb-2 text-center w-full">
          Results: {results.length} | HasMore: {hasMore ? 'Yes' : 'No'} | Loading: {loadingMore ? 'Yes' : 'No'}
        </div> */}
        
        {hasMore && !loadingMore && (
          <button
            onClick={() => {
              // console.log('Load More clicked!');
              loadMore();
            }}
            disabled={loadingMore}
            className="bg-[#00559B] text-white font-semibold px-8 py-3 rounded-lg shadow-lg 
                      hover:bg-[#004080] hover:scale-[1.05] active:scale-[0.98] 
                      transition-all duration-300 ease-in-out
                      disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
                      min-w-[200px] flex items-center justify-center"
          >
            <div className="flex items-center">
              {/* <svg 
                className="w-5 h-5 mr-2" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg> */}
              Load More Articles
            </div>
          </button>
        )}
        
        {loadingMore && (
          <div className="flex items-center text-gray-600">
            <svg 
              className="animate-spin h-5 w-5 mr-2" 
              xmlns="http://www.w3.org/2000/svg" 
              fill="none" 
              viewBox="0 0 24 24"
            >
              <circle 
                className="opacity-25" 
                cx="12" 
                cy="12" 
                r="10" 
                stroke="currentColor" 
                strokeWidth="4"
              ></circle>
              <path 
                className="opacity-75" 
                fill="currentColor" 
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            Loading More Articles...
          </div>
        )}
        
        {/* Show message when no more articles */}
        {!hasMore && results.length > 0 && (
          <div className="text-center text-gray-500 py-4">
            <p className="text-lg font-medium">No more articles to load</p>
            <p className="text-sm mt-1">You've reached the end of the results</p>
          </div>
        )}
      </div>
    </div>
  );
}