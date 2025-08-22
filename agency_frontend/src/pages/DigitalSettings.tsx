import { useEffect, useState } from 'react';
import { API_URL } from '../api';

interface Service { id: number; name: string }

export default function DigitalSettings() {
  const token = localStorage.getItem('token');
  const [services, setServices] = useState<Service[]>([]);
  const [show, setShow] = useState(false);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [localServices, setLocalServices] = useState<Service[]>([]);
  const [nextId, setNextId] = useState(1000); // Start with high ID to avoid conflicts

  const load = async () => {
    if (!token) {
      setServices([]);
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/digital/services`, { 
        headers: { Authorization: `Bearer ${token}` } 
      });
      if (res.ok) {
        const data = await res.json();
        setServices(Array.isArray(data) ? data : []);
      } else {
        setServices([]);
      }
    } catch (error) {
      setServices([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const add = async () => {
    if (!name.trim()) return;
    
    // First try to add via API
    try {
      const res = await fetch(`${API_URL}/digital/services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: name.trim() })
      });
      if (res.ok) {
        const newService = await res.json();
        setServices(Array.isArray(services) ? [...services, newService] : [newService]);
        setShow(false);
        setName('');
        return;
      }
    } catch (error) {
      console.error('API failed, adding locally:', error);
    }
    
    // If API fails, add locally
    const newLocalService: Service = {
      id: nextId,
      name: name.trim()
    };
    setLocalServices(prev => [...prev, newLocalService]);
    setNextId(prev => prev + 1);
    setShow(false);
    setName('');
  };

  const remove = async (id: number) => {
    // Check if it's a local service first
    const isLocalService = localServices.some(s => s.id === id);
    
    if (isLocalService) {
      // Remove from local services
      setLocalServices(prev => prev.filter(s => s.id !== id));
      return;
    }
    
    // For API services, try to delete via API
    try {
      const res = await fetch(`${API_URL}/digital/services/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (res.ok) {
        // Successfully deleted from API, remove from UI
        setServices(Array.isArray(services) ? services.filter(s => s.id !== id) : []);
      } else {
        console.error('Failed to delete service: Server responded with', res.status);
        // Don't remove from UI if API deletion failed
      }
    } catch (error) {
      console.error('Failed to remove service:', error);
      // Don't remove from UI if there was a network error
    }
  };


  return (
    <div className="w-full overflow-hidden bg-gray-50 min-h-screen">
      <div className="bg-white shadow-sm border-b p-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Digital Настройки</h1>
            <p className="text-gray-600 mt-1">Управляйте настройками и услугами digital отдела</p>
          </div>
        </div>
      </div>
      
      <div className="p-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">Digital услуги</h2>
              <button 
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-lg font-medium shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center space-x-2"
                onClick={() => setShow(true)}
              >
                <span>+</span>
                <span>Добавить услугу</span>
              </button>
            </div>
          </div>
          
          <div className="p-6">
            {loading ? (
              <div className="text-center py-8">
                <div className="text-gray-400 text-4xl mb-4">⏳</div>
                <p className="text-gray-500">Загрузка услуг...</p>
              </div>
            ) : (() => {
              const allServices = [...(Array.isArray(services) ? services : []), ...localServices];
              return allServices.length > 0 ? (
                <div className="grid gap-4">
                  {allServices.map(service => {
                    const isLocal = localServices.some(s => s.id === service.id);
                    return (
                      <div key={service.id} className="flex justify-between items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors">
                        <div className="flex items-center space-x-3">
                          <div className={`w-3 h-3 rounded-full ${isLocal ? 'bg-green-500' : 'bg-blue-500'}`}></div>
                          <span className="text-gray-900 font-medium">{service.name}</span>
                          {isLocal && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              Локально
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => remove(service.id)}
                          className="text-red-600 hover:text-red-800 hover:bg-red-50 px-3 py-1.5 rounded-md transition-colors text-sm font-medium"
                        >
                          Удалить
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="text-gray-400 text-6xl mb-4">⚙️</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Нет услуг</h3>
                  <p className="text-gray-500">Добавьте первую digital услугу!</p>
                </div>
              );
            })()}
          </div>
        </div>
      </div>

      {show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-96 overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900">Новая digital услуга</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Название услуги
                </label>
                <input 
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" 
                  placeholder="Введите название услуги" 
                  value={name} 
                  onChange={e => setName(e.target.value)}
                  onKeyPress={e => e.key === 'Enter' && add()}
                />
              </div>
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors font-medium"
                onClick={() => { setShow(false); setName(''); }}
              >
                Отмена
              </button>
              <button 
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={add}
                disabled={!name.trim()}
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
