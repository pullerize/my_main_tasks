import React, { useState, useEffect } from 'react';
import { Plus, Trash2, X, Save, AlertCircle, Receipt } from 'lucide-react';
import { authFetch, API_URL } from '../api';


interface CommonExpense {
  id: number;
  name: string;
  amount: number;
  description?: string;
  category_id?: number;
  date: string;
  created_at: string;
}

const ExpenseSettings: React.FC = () => {
  const [commonExpenses, setCommonExpenses] = useState<CommonExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    amount: 0,
    date: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    loadAllData();
    
    // Fallback timeout - stop loading after 10 seconds
    const timeout = setTimeout(() => {
      setLoading(false);
    }, 10000);
    
    return () => clearTimeout(timeout);
  }, []);

  const loadAllData = async () => {
    try {
      console.log('Loading common expenses...');
      setLoading(true);

      const response = await authFetch(`${API_URL}/common-expenses/`);
      
      if (response.ok) {
        const commonData = await response.json();
        setCommonExpenses(commonData || []);
      }

    } catch (error) {
      console.error('Failed to load data:', error);
      setCommonExpenses([]);
    } finally {
      setLoading(false);
    }
  };

  const openModal = () => {
    setShowModal(true);
    resetForm();
  };

  const closeModal = () => {
    setShowModal(false);
    resetForm();
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      amount: 0,
      date: new Date().toISOString().split('T')[0]
    });
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.name || formData.amount <= 0) {
      alert('Пожалуйста, заполните все обязательные поля');
      return;
    }
    
    try {
      const data = {
        name: formData.name,
        amount: formData.amount,
        description: formData.description
      };

      const response = await authFetch(`${API_URL}/common-expenses/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        await loadAllData();
        closeModal();
      } else {
        throw new Error('Failed to create expense');
      }
    } catch (error) {
      console.error('Failed to create:', error);
      alert('Ошибка при создании расхода. Попробуйте снова.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот расход?')) {
      return;
    }

    try {
      const response = await authFetch(`${API_URL}/common-expenses/${id}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await loadAllData();
      } else {
        throw new Error('Failed to delete expense');
      }
    } catch (error) {
      console.error('Failed to delete:', error);
      alert('Ошибка при удалении расхода. Попробуйте снова.');
    }
  };

  if (loading) {
    return (
      <div className="p-6 bg-gray-50 min-h-screen">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Загружаем управление расходами...</p>
            <button 
              onClick={() => setLoading(false)}
              className="mt-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Пропустить загрузку
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Управление расходами</h1>
        </div>

        {/* Common Expenses Section */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Расходы</h2>
            <button
              onClick={() => openModal()}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
            >
              <Plus size={16} />
              Добавить расход
            </button>
          </div>

            {/* Common Expenses Table */}
            <div className="overflow-x-auto">
              <table className="w-full table-auto">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Название</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Сумма</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Описание</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Дата</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {(commonExpenses || []).map((expense) => (
                    <tr key={expense.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{expense.name}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900">{expense.amount.toLocaleString('ru-RU')} сум</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-gray-600">{expense.description || '—'}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {expense.date ? new Date(expense.date).toLocaleDateString('ru-RU') : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(expense.id)}
                          className="text-red-600 hover:text-red-800"
                          title="Удалить"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {commonExpenses.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                        Нет расходов
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>


        {/* Modal */}
        {showModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">
                  Новый расход
                </h3>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleCreate} className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Название *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                {/* Amount */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Сумма *
                  </label>
                  <input
                    type="number"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                    min="0"
                    step="0.01"
                  />
                </div>


                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Описание
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                  />
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4">
                  <button
                    type="button"
                    onClick={closeModal}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-white rounded-md bg-green-600 hover:bg-green-700"
                  >
                    <Save size={16} className="inline mr-2" />
                    Сохранить
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExpenseSettings;