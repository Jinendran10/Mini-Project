import React, { useState, useEffect } from 'react';
import { Menu, Home, BarChart3, MessageSquare, Settings, LogOut } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(true);
  const location = useLocation();

  const menuItems = [
    { label: 'Home', icon: Home, path: '/' },
    { label: 'Dashboard', icon: BarChart3, path: '/dashboard' },
    { label: 'Chatbot', icon: MessageSquare, path: '/chatbot' },
    { label: 'Settings', icon: Settings, path: '/settings' },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <>
      {/* Mobile toggle button */}
      <button
        className="md:hidden fixed top-4 left-4 z-50 bg-gray-900 text-white p-2 rounded"
        onClick={() => setIsOpen(!isOpen)}
      >
        <Menu size={24} />
      </button>

      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 h-screen w-64 bg-darker text-white overflow-y-auto transform transition-transform duration-300 border-r border-primary/20 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 md:relative z-40`}
        style={{ background: 'linear-gradient(180deg, #0a0a0f 0%, #1a0a2e 100%)' }}
      >
        {/* Logo */}
        <div className="p-6 border-b border-primary/30">
          <h1 className="text-2xl font-bold gta-glow">🛡️ Poison Guard</h1>
          <p className="text-xs text-gray-400 mt-1">AI Defense System</p>
        </div>

        {/* Menu Items */}
        <nav className="p-4 space-y-2">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-300 ${
                isActive(item.path)
                  ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-lg shadow-primary/50'
                  : 'text-gray-300 hover:bg-primary/10 hover:border hover:border-primary/30 hover:text-primary'
              }`}
              onClick={() => setIsOpen(false)}
            >
              <item.icon size={20} className="flex-shrink-0" />
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-primary/30">
          <button className="flex items-center space-x-3 w-full px-4 py-3 text-gray-300 hover:text-primary hover:bg-primary/10 rounded-lg transition-all duration-300">
            <LogOut size={20} className="flex-shrink-0" />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </div>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 md:hidden z-30"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
