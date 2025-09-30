import React from 'react';
import { useSidebar } from '../contexts/SidebarContext';

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'warning' | 'danger' | 'info';
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  type = 'warning'
}) => {
  const { isCollapsed } = useSidebar();

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const getIconColor = () => {
    switch (type) {
      case 'danger': return 'text-red-500';
      case 'info': return 'text-blue-500';
      default: return 'text-yellow-500';
    }
  };

  const getConfirmButtonStyle = () => {
    switch (type) {
      case 'danger': return 'bg-red-500 hover:bg-red-600 focus:ring-red-500';
      case 'info': return 'bg-blue-500 hover:bg-blue-600 focus:ring-blue-500';
      default: return 'bg-yellow-500 hover:bg-yellow-600 focus:ring-yellow-500';
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
      style={{
        zIndex: 9999
      }}
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full transform transition-all duration-200 scale-100">
        <div className="p-6">
          <div className="flex items-center mb-4">
            <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${getIconColor()} bg-opacity-10`}>
              {type === 'danger' && (
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              )}
              {type === 'warning' && (
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              )}
              {type === 'info' && (
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <h3 className="ml-3 text-base lg:text-sm font-medium text-gray-900">{title}</h3>
          </div>

          <p className="text-sm lg:text-xs text-gray-600 mb-6">{message}</p>

          <div className="flex space-x-3 justify-end">
            <button
              type="button"
              className="px-4 py-2 text-sm lg:text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-200"
              onClick={onClose}
            >
              {cancelText}
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm lg:text-xs font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200 ${getConfirmButtonStyle()}`}
              onClick={handleConfirm}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};