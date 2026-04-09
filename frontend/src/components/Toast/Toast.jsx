import { useEffect, useContext } from 'react';
import { styled, keyframes } from 'styled-components';
import { ToastContext } from '../../context/ToastContext';

const fadeIn = keyframes`
  from { 
    opacity: 0; 
    transform: translate(-50%, -20px); 
  }
  to { 
    opacity: 1; 
    transform: translate(-50%, 0); 
  }
`;

const fadeOut = keyframes`
  from { 
    opacity: 1; 
    transform: translate(-50%, 0); 
  }
  to { 
    opacity: 0; 
    transform: translate(-50%, -20px); 
  }
`;

const ToastContainer = styled.div`
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  animation: ${({ $isVisible }) => ($isVisible ? fadeIn : fadeOut)} 0.3s ease-in-out;
  animation-fill-mode: forwards;
  width: auto;
  max-width: 90vw;
  
  @media (max-width: 768px) {
    top: 10px;
    max-width: 95vw;
  }
  
  @media (max-width: 480px) {
    top: 5px;
    width: calc(100% - 20px);
  }
`;

const ToastMessage = styled.div`
  padding: 12px 24px;
  border-radius: 8px;
  color: white;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  text-align: center;
  word-break: break-word;
  background-color: ${({ $type }) => {
    switch ($type) {
      case 'success':
        return '#10B981';
      case 'error':
        return '#EF4444';
      case 'warning':
        return '#F59E0B';
      case 'info':
      default:
        return '#3B82F6';
    }
  }};
  
  @media (max-width: 768px) {
    padding: 10px 20px;
    font-size: 14px;
  }
  
  @media (max-width: 480px) {
    padding: 8px 16px;
    font-size: 13px;
  }
`;

const Toast = () => {
  const { toast, hideToast } = useContext(ToastContext);
  const { message, type, isVisible, duration = 3000 } = toast;

  useEffect(() => {
    let timer;
    if (isVisible && duration > 0) {
      timer = setTimeout(() => {
        hideToast();
      }, duration);
    }
    return () => clearTimeout(timer);
  }, [isVisible, hideToast, duration]);

  if (!isVisible || !message) return null;

  return (
    <ToastContainer $isVisible={isVisible}>
      <ToastMessage $type={type}>
        {message}
      </ToastMessage>
    </ToastContainer>
  );
};

export default Toast;