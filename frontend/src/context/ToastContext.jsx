import { createContext, useContext, useState } from 'react';

const ToastContext = createContext(null);

export const ToastProvider = ({ children }) => {
  const [toast, setToast] = useState({
    message: '',
    type: 'info',
    isVisible: false,
  });

  const showToast = (message, type = 'info', duration = 3000) => {
    setToast({
      message,
      type,
      isVisible: true,
    });

    // Auto-hide after duration
    setTimeout(() => {
      hideToast();
    }, duration);
  };

  const hideToast = () => {
    setToast(prev => ({
      ...prev,
      isVisible: false,
    }));
  };

  return (
    <ToastContext.Provider value={{ showToast, hideToast, toast }}>
      {children}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

export { ToastContext };
export default ToastContext;
