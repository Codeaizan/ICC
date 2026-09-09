const STORAGE_KEY = 'aspects_history';

// Generate a random ID if none provided
export const generateId = () => {
  return `STK-${Math.floor(Math.random() * 900) + 100}`;
};

export const getHistory = () => {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Error reading from localStorage', error);
    return [];
  }
};

export const saveScan = (scanData) => {
  try {
    const history = getHistory();
    const existingIndex = history.findIndex(s => s.id === scanData.id);
    if (existingIndex >= 0) {
      history[existingIndex] = { ...history[existingIndex], ...scanData };
    } else {
      history.unshift({
        ...scanData,
        date: new Date().toISOString(),
      });
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    return true;
  } catch (error) {
    console.error('Error saving to localStorage', error);
    return false;
  }
};

export const getScanById = async (id) => {
  try {
    const response = await fetch(`http://localhost:8000/api/case/${id}`);
    if (!response.ok) {
      // Fallback to local history
      const history = getHistory();
      return history.find(s => s.id === id) || null;
    }
    const data = await response.json();
    
    // Map Python result.json to frontend format
    const allRegions = ['Caudate', 'Lentiform Nucleus', 'Insula', 'Internal Capsule', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6'];
    const nameMap = {
      'Caudate': 'caudate',
      'Lentiform Nucleus': 'lentiform',
      'Insula': 'insula',
      'Internal Capsule': 'internal_capsule',
      'M1': 'M1', 'M2': 'M2', 'M3': 'M3', 'M4': 'M4', 'M5': 'M5', 'M6': 'M6'
    };

    const regionsData = allRegions.map(uiName => {
      const pythonName = nameMap[uiName];
      // Find region in the python regions array
      const regionData = data.regions.find(r => r.name === pythonName) || { affected: false, evidence: 'none' };
      const isAbnormal = regionData.affected;
      return {
        name: uiName,
        status: isAbnormal ? 'abnormal' : 'normal',
        confidence: isAbnormal ? 99 : 99,
        evidence: regionData.evidence
      };
    });
    
    const scanData = {
      id: id,
      modality: 'NCCT',
      sliceThickness: '5mm',
      regions: regionsData,
      abnormalCount: 10 - data.aspects,
      score: data.aspects,
      status: 'Completed'
    };
    
    saveScan(scanData);
    return scanData;
  } catch (error) {
    console.error("Failed to fetch from backend:", error);
    const history = getHistory();
    return history.find(s => s.id === id) || null;
  }
};

export const clearHistory = () => {
  localStorage.removeItem(STORAGE_KEY);
};
