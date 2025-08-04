import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [musician, setMusician] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    const storedMusician = localStorage.getItem('musician');
    if (storedMusician && token) {
      setMusician(JSON.parse(storedMusician));
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, [token]);

  const login = (authData) => {
    setMusician(authData.musician);
    setToken(authData.token);
    localStorage.setItem('token', authData.token);
    localStorage.setItem('musician', JSON.stringify(authData.musician));
    axios.defaults.headers.common['Authorization'] = `Bearer ${authData.token}`;
  };

  const logout = () => {
    setMusician(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('musician');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ musician, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

// Realtime Service (structured for easy WebSocket upgrade)
class RealtimeService {
  constructor(musicianId, onUpdate) {
    this.musicianId = musicianId;
    this.onUpdate = onUpdate;
    this.polling = false;
    this.interval = null;
  }

  startPolling() {
    if (this.polling) return;
    this.polling = true;
    
    this.fetchUpdates();
    this.interval = setInterval(() => {
      this.fetchUpdates();
    }, 3000); // Poll every 3 seconds
  }

  stopPolling() {
    this.polling = false;
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  async fetchUpdates() {
    try {
      const response = await axios.get(`${API}/requests/updates/${this.musicianId}`);
      this.onUpdate(response.data);
    } catch (error) {
      console.error('Error fetching updates:', error);
    }
  }

  // Future WebSocket method (placeholder)
  connectWebSocket() {
    // TODO: Implement WebSocket connection
    // const ws = new WebSocket(`ws://localhost:8001/ws/musician/${this.musicianId}`);
    // ws.onmessage = (event) => this.onUpdate(JSON.parse(event.data));
  }
}

// Components
const AuthForm = ({ mode, onSwitch }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const endpoint = mode === 'login' ? 'auth/login' : 'auth/register';
      const payload = mode === 'login' 
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await axios.post(`${API}/${endpoint}`, payload);
      login(response.data);
      navigate('/dashboard');
    } catch (error) {
      setError(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">RequestWave</h1>
          <p className="text-purple-200">Connect with your audience through music</p>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl">
          <h2 className="text-2xl font-bold text-white text-center mb-6">
            {mode === 'login' ? 'Welcome Back' : 'Join RequestWave'}
          </h2>

          {error && (
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <input
                type="text"
                placeholder="Your Stage Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            )}
            
            <input
              type="email"
              placeholder="Email Address"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
              required
            />
            
            <input
              type="password"
              placeholder="Password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
              required
            />
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold py-3 rounded-lg transition duration-300 disabled:opacity-50"
            >
              {loading ? 'Please wait...' : (mode === 'login' ? 'Sign In' : 'Create Account')}
            </button>
          </form>

          <div className="text-center mt-6">
            <button
              onClick={() => onSwitch(mode === 'login' ? 'register' : 'login')}
              className="text-purple-300 hover:text-white transition duration-300"
            >
              {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const MusicianDashboard = () => {
  const { musician, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('songs');
  const [songs, setSongs] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [realtimeService, setRealtimeService] = useState(null);

  // CSV Upload state
  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvError, setCsvError] = useState('');
  const [showCsvUpload, setShowCsvUpload] = useState(false);

  // Song form state
  const [songForm, setSongForm] = useState({
    title: '',
    artist: '',
    genres: [],
    moods: [],
    year: '',
    notes: ''
  });

  // Song editing state
  const [editingSong, setEditingSong] = useState(null);
  const [songError, setSongError] = useState('');

  // Profile management state
  const [showProfile, setShowProfile] = useState(false);
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    venmo_link: '',
    bio: '',
    website: ''
  });
  const [profileError, setProfileError] = useState('');

  useEffect(() => {
    fetchSongs();
    fetchRequests();
    
    // Setup real-time updates
    const service = new RealtimeService(musician.id, (data) => {
      setRequests(data.requests);
    });
    setRealtimeService(service);
    service.startPolling();

    return () => {
      if (service) service.stopPolling();
    };
  }, [musician.id]);

  useEffect(() => {
    if (showProfile) {
      fetchProfile();
    }
  }, [showProfile]);

  const fetchSongs = async () => {
    try {
      const response = await axios.get(`${API}/songs`);
      setSongs(response.data);
    } catch (error) {
      console.error('Error fetching songs:', error);
    }
  };

  const fetchRequests = async () => {
    try {
      const response = await axios.get(`${API}/requests/musician/${musician.id}`);
      setRequests(response.data);
    } catch (error) {
      console.error('Error fetching requests:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSong = async (e) => {
    e.preventDefault();
    setSongError('');
    
    try {
      const songData = {
        ...songForm,
        genres: songForm.genres.filter(g => g.trim()),
        moods: songForm.moods.filter(m => m.trim()),
        year: songForm.year ? parseInt(songForm.year) : null
      };
      
      await axios.post(`${API}/songs`, songData);
      setSongForm({
        title: '',
        artist: '',
        genres: [],
        moods: [],
        year: '',
        notes: ''
      });
      fetchSongs();
    } catch (error) {
      setSongError(error.response?.data?.detail || 'Error adding song');
    }
  };

  const handleEditSong = (song) => {
    setEditingSong(song);
    setSongForm({
      title: song.title,
      artist: song.artist,
      genres: song.genres,
      moods: song.moods,
      year: song.year ? song.year.toString() : '',
      notes: song.notes
    });
    setSongError('');
  };

  const handleUpdateSong = async (e) => {
    e.preventDefault();
    setSongError('');
    
    try {
      const songData = {
        ...songForm,
        genres: songForm.genres.filter(g => g.trim()),
        moods: songForm.moods.filter(m => m.trim()),
        year: songForm.year ? parseInt(songForm.year) : null
      };
      
      await axios.put(`${API}/songs/${editingSong.id}`, songData);
      setEditingSong(null);
      setSongForm({
        title: '',
        artist: '',
        genres: [],
        moods: [],
        year: '',
        notes: ''
      });
      fetchSongs();
    } catch (error) {
      setSongError(error.response?.data?.detail || 'Error updating song');
    }
  };

  const cancelEdit = () => {
    setEditingSong(null);
    setSongForm({
      title: '',
      artist: '',
      genres: [],
      moods: [],
      year: '',
      notes: ''
    });
    setSongError('');
  };

  const handleDeleteSong = async (songId) => {
    if (window.confirm('Are you sure you want to delete this song?')) {
      try {
        await axios.delete(`${API}/songs/${songId}`);
        fetchSongs();
      } catch (error) {
        console.error('Error deleting song:', error);
      }
    }
  };

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`);
      setProfile(response.data);
    } catch (error) {
      setProfileError('Error loading profile');
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setProfileError('');
    
    try {
      const response = await axios.put(`${API}/profile`, profile);
      setProfile(response.data);
      setShowProfile(false);
      alert('Profile updated successfully!');
    } catch (error) {
      setProfileError(error.response?.data?.detail || 'Error updating profile');
    }
  };

  const updateRequestStatus = async (requestId, status) => {
    try {
      await axios.put(`${API}/requests/${requestId}/status?status=${status}`);
      fetchRequests();
    } catch (error) {
      console.error('Error updating request:', error);
    }
  };

  // CSV Upload functions
  const handleCsvFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCsvFile(file);
      setCsvPreview(null);
      setCsvError('');
    }
  };

  const handleCsvDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith('.csv')) {
      setCsvFile(file);
      setCsvPreview(null);
      setCsvError('');
    } else {
      setCsvError('Please drop a valid CSV file');
    }
  };

  const previewCsv = async () => {
    if (!csvFile) return;
    
    setCsvUploading(true);
    setCsvError('');
    
    try {
      const formData = new FormData();
      formData.append('file', csvFile);
      
      const response = await axios.post(`${API}/songs/csv/preview`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setCsvPreview(response.data);
    } catch (error) {
      setCsvError(error.response?.data?.detail || 'Error previewing CSV file');
    } finally {
      setCsvUploading(false);
    }
  };

  const uploadCsv = async () => {
    if (!csvFile) return;
    
    setCsvUploading(true);
    setCsvError('');
    
    try {
      const formData = new FormData();
      formData.append('file', csvFile);
      
      const response = await axios.post(`${API}/songs/csv/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Reset form and refresh songs
      setCsvFile(null);
      setCsvPreview(null);
      setShowCsvUpload(false);
      fetchSongs();
      
      alert(`Success! ${response.data.songs_added} songs imported${response.data.errors.length > 0 ? ' with some warnings' : ''}`);
      
    } catch (error) {
      setCsvError(error.response?.data?.detail || 'Error uploading CSV file');
    } finally {
      setCsvUploading(false);
    }
  };

  const audienceUrl = `${window.location.origin}/musician/${musician.slug}`;

  if (loading) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-purple-400">RequestWave</h1>
            <div className="flex items-center space-x-4">
              <span className="text-gray-300">Welcome, {musician.name}</span>
              <button
                onClick={logout}
                className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg transition duration-300"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Audience Link */}
        <div className="bg-purple-800/50 rounded-xl p-6 mb-8">
          <h2 className="text-xl font-bold mb-2">Your Audience Link</h2>
          <p className="text-purple-200 mb-4">Share this link with your audience for song requests:</p>
          <div className="flex items-center space-x-4">
            <input
              type="text"
              value={audienceUrl}
              readOnly
              className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
            />
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(audienceUrl);
                  // Provide visual feedback
                  const button = event.target;
                  const originalText = button.textContent;
                  button.textContent = 'Copied!';
                  button.style.backgroundColor = '#059669'; // green-600
                  setTimeout(() => {
                    button.textContent = originalText;
                    button.style.backgroundColor = ''; // reset to original
                  }, 2000);
                } catch (err) {
                  console.error('Failed to copy text: ', err);
                  // Fallback for browsers that don't support clipboard API
                  const textArea = document.createElement('textarea');
                  textArea.value = audienceUrl;
                  document.body.appendChild(textArea);
                  textArea.select();
                  document.execCommand('copy');
                  document.body.removeChild(textArea);
                  
                  // Provide visual feedback for fallback
                  const button = event.target;
                  const originalText = button.textContent;
                  button.textContent = 'Copied!';
                  button.style.backgroundColor = '#059669';
                  setTimeout(() => {
                    button.textContent = originalText;
                    button.style.backgroundColor = '';
                  }, 2000);
                }
              }}
              className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition duration-300"
            >
              Copy
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 bg-gray-800 rounded-lg p-1 mb-8">
          {['songs', 'requests', 'profile'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition duration-300 ${
                activeTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'requests' && requests.filter(r => r.status === 'pending').length > 0 && (
                <span className="ml-2 bg-red-500 text-white rounded-full px-2 py-1 text-xs">
                  {requests.filter(r => r.status === 'pending').length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Songs Tab */}
        {activeTab === 'songs' && (
          <div>
            {/* Song Management Header */}
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Song Management</h2>
              <button
                onClick={() => setShowCsvUpload(!showCsvUpload)}
                className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-bold transition duration-300"
              >
                {showCsvUpload ? 'Hide CSV Upload' : 'Upload CSV'}
              </button>
            </div>

            {/* CSV Upload Section */}
            {showCsvUpload && (
              <div className="bg-gray-800 rounded-xl p-6 mb-8">
                <h3 className="text-lg font-bold mb-4">Upload Songs from CSV</h3>
                <p className="text-gray-300 mb-4 text-sm">
                  Expected CSV format: Title, Artist, Genre, Mood, Year, Notes
                  <br />
                  <span className="text-purple-300">Genres and Moods can be comma-separated (e.g., "Rock, Jazz")</span>
                </p>

                {!csvFile ? (
                  <div
                    className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-purple-500 transition duration-300"
                    onDrop={handleCsvDrop}
                    onDragOver={(e) => e.preventDefault()}
                    onClick={() => document.getElementById('csvFileInput').click()}
                  >
                    <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                      <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <p className="text-gray-300">
                      <span className="font-bold text-purple-400">Click to upload</span> or drag and drop
                    </p>
                    <p className="text-gray-400 text-sm">CSV files only (max 5MB)</p>
                    <input
                      id="csvFileInput"
                      type="file"
                      accept=".csv"
                      onChange={handleCsvFileSelect}
                      className="hidden"
                    />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* File Info */}
                    <div className="bg-gray-700 rounded-lg p-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-bold">{csvFile.name}</p>
                          <p className="text-sm text-gray-300">{(csvFile.size / 1024).toFixed(1)} KB</p>
                        </div>
                        <button
                          onClick={() => {
                            setCsvFile(null);
                            setCsvPreview(null);
                            setCsvError('');
                          }}
                          className="text-red-400 hover:text-red-300"
                        >
                          Remove
                        </button>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex space-x-4">
                      <button
                        onClick={previewCsv}
                        disabled={csvUploading}
                        className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                      >
                        {csvUploading ? 'Processing...' : 'Preview'}
                      </button>
                      {csvPreview && (
                        <button
                          onClick={uploadCsv}
                          disabled={csvUploading}
                          className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                        >
                          {csvUploading ? 'Uploading...' : `Import ${csvPreview.valid_rows} Songs`}
                        </button>
                      )}
                    </div>

                    {/* CSV Preview */}
                    {csvPreview && (
                      <div className="bg-gray-700 rounded-lg p-4">
                        <h4 className="font-bold mb-2">
                          Preview: {csvPreview.valid_rows} of {csvPreview.total_rows} rows valid
                        </h4>
                        
                        {csvPreview.errors.length > 0 && (
                          <div className="mb-4">
                            <h5 className="text-red-400 font-bold mb-2">Errors:</h5>
                            <div className="bg-red-900/20 rounded p-2 max-h-32 overflow-y-auto">
                              {csvPreview.errors.map((error, idx) => (
                                <p key={idx} className="text-red-300 text-sm">{error}</p>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-gray-600">
                                <th className="text-left p-2">Title</th>
                                <th className="text-left p-2">Artist</th>
                                <th className="text-left p-2">Genres</th>
                                <th className="text-left p-2">Moods</th>
                                <th className="text-left p-2">Year</th>
                              </tr>
                            </thead>
                            <tbody>
                              {csvPreview.preview.map((song, idx) => (
                                <tr key={idx} className="border-b border-gray-600">
                                  <td className="p-2">{song.title}</td>
                                  <td className="p-2">{song.artist}</td>
                                  <td className="p-2">{song.genres.join(', ')}</td>
                                  <td className="p-2">{song.moods.join(', ')}</td>
                                  <td className="p-2">{song.year || '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {csvError && (
                      <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-red-200">
                        {csvError}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Add Song Form */}
            <div className="bg-gray-800 rounded-xl p-6 mb-8">
              <h2 className="text-xl font-bold mb-4">
                {editingSong ? 'Edit Song' : 'Add New Song'}
              </h2>
              
              {songError && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                  {songError}
                </div>
              )}
              
              <form onSubmit={editingSong ? handleUpdateSong : handleAddSong} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Song Title"
                  value={songForm.title}
                  onChange={(e) => setSongForm({...songForm, title: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  required
                />
                <input
                  type="text"
                  placeholder="Artist"
                  value={songForm.artist}
                  onChange={(e) => setSongForm({...songForm, artist: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  required
                />
                <input
                  type="text"
                  placeholder="Genres (comma separated)"
                  value={songForm.genres.join(', ')}
                  onChange={(e) => setSongForm({...songForm, genres: e.target.value.split(',').map(g => g.trim())})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                <input
                  type="text"
                  placeholder="Moods (comma separated)"
                  value={songForm.moods.join(', ')}
                  onChange={(e) => setSongForm({...songForm, moods: e.target.value.split(',').map(m => m.trim())})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                <input
                  type="number"
                  placeholder="Year"
                  value={songForm.year}
                  onChange={(e) => setSongForm({...songForm, year: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                <input
                  type="text"
                  placeholder="Notes (optional)"
                  value={songForm.notes}
                  onChange={(e) => setSongForm({...songForm, notes: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                <div className="md:col-span-2 flex space-x-4">
                  <button
                    type="submit"
                    className="flex-1 bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300"
                  >
                    {editingSong ? 'Update Song' : 'Add Song'}
                  </button>
                  {editingSong && (
                    <button
                      type="button"
                      onClick={cancelEdit}
                      className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-bold transition duration-300"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            </div>

            {/* Songs List */}
            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-bold mb-4">Your Songs ({songs.length})</h2>
              <div className="space-y-4">
                {songs.map((song) => (
                  <div key={song.id} className="bg-gray-700 rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-bold text-lg">{song.title}</h3>
                        <p className="text-gray-300">by {song.artist}</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {song.genres.map((genre, idx) => (
                            <span key={idx} className="bg-blue-600 text-xs px-2 py-1 rounded">{genre}</span>
                          ))}
                          {song.moods.map((mood, idx) => (
                            <span key={idx} className="bg-green-600 text-xs px-2 py-1 rounded">{mood}</span>
                          ))}
                          {song.year && <span className="bg-gray-600 text-xs px-2 py-1 rounded">{song.year}</span>}
                        </div>
                        {song.notes && (
                          <p className="text-gray-400 text-sm mt-2 italic">"{song.notes}"</p>
                        )}
                      </div>
                      <div className="flex space-x-2 ml-4">
                        <button
                          onClick={() => handleEditSong(song)}
                          className="bg-blue-600 hover:bg-blue-700 text-xs px-3 py-1 rounded transition duration-300"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteSong(song.id)}
                          className="bg-red-600 hover:bg-red-700 text-xs px-3 py-1 rounded transition duration-300"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {songs.length === 0 && (
                  <p className="text-gray-400 text-center py-8">No songs added yet. Add your first song above!</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Requests Tab */}
        {activeTab === 'requests' && (
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-xl font-bold mb-4">Song Requests ({requests.length})</h2>
            <div className="space-y-4">
              {requests.map((request) => (
                <div key={request.id} className="bg-gray-700 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg">{request.song_title}</h3>
                      <p className="text-gray-300">by {request.song_artist}</p>
                      <p className="text-purple-300 mt-2">Requested by: {request.requester_name}</p>
                      {request.dedication && (
                        <p className="text-gray-400 italic mt-1">"{request.dedication}"</p>
                      )}
                      {request.tip_amount > 0 && (
                        <p className="text-green-400 font-bold mt-1">Tip: ${request.tip_amount}</p>
                      )}
                    </div>
                    <div className="flex flex-col space-y-2 ml-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        request.status === 'pending' ? 'bg-yellow-600' :
                        request.status === 'accepted' ? 'bg-blue-600' :
                        request.status === 'played' ? 'bg-green-600' :
                        'bg-red-600'
                      }`}>
                        {request.status.toUpperCase()}
                      </span>
                      {request.status === 'pending' && (
                        <div className="flex space-x-1">
                          <button
                            onClick={() => updateRequestStatus(request.id, 'accepted')}
                            className="bg-green-600 hover:bg-green-700 text-xs px-2 py-1 rounded"
                          >
                            Accept
                          </button>
                          <button
                            onClick={() => updateRequestStatus(request.id, 'rejected')}
                            className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1 rounded"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                      {request.status === 'accepted' && (
                        <button
                          onClick={() => updateRequestStatus(request.id, 'played')}
                          className="bg-purple-600 hover:bg-purple-700 text-xs px-2 py-1 rounded"
                        >
                          Mark Played
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {requests.length === 0 && (
                <p className="text-gray-400 text-center py-8">No requests yet. Share your audience link to start receiving requests!</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const AudienceInterface = () => {
  const { slug } = useParams();
  const [musician, setMusician] = useState(null);
  const [songs, setSongs] = useState([]);
  const [filteredSongs, setFilteredSongs] = useState([]);
  const [filters, setFilters] = useState({});
  const [selectedFilters, setSelectedFilters] = useState({
    genre: '',
    artist: '',
    mood: '',
    year: ''
  });
  const [requestForm, setRequestForm] = useState({
    requester_name: '',
    requester_email: '',
    dedication: '',
    tip_amount: 0
  });
  const [selectedSong, setSelectedSong] = useState(null);
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchMusician();
    fetchSongs();
    fetchFilters();
  }, [slug]);

  useEffect(() => {
    applyFilters();
  }, [songs, selectedFilters]);

  const fetchMusician = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${slug}`);
      setMusician(response.data);
    } catch (error) {
      console.error('Error fetching musician:', error);
    }
  };

  const fetchSongs = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${slug}/songs`);
      setSongs(response.data);
    } catch (error) {
      console.error('Error fetching songs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFilters = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${slug}/filters`);
      setFilters(response.data);
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const applyFilters = () => {
    let filtered = [...songs];

    if (selectedFilters.genre) {
      filtered = filtered.filter(song => song.genres.includes(selectedFilters.genre));
    }
    if (selectedFilters.artist) {
      filtered = filtered.filter(song => 
        song.artist.toLowerCase().includes(selectedFilters.artist.toLowerCase())
      );
    }
    if (selectedFilters.mood) {
      filtered = filtered.filter(song => song.moods.includes(selectedFilters.mood));
    }
    if (selectedFilters.year) {
      filtered = filtered.filter(song => song.year === parseInt(selectedFilters.year));
    }

    setFilteredSongs(filtered);
  };

  const handleRequest = async (song) => {
    if (!requestForm.requester_name || !requestForm.requester_email) {
      alert('Please enter your name and email');
      return;
    }

    try {
      await axios.post(`${API}/requests`, {
        song_id: song.id,
        ...requestForm,
        tip_amount: parseFloat(requestForm.tip_amount) || 0
      });
      
      setSuccess('Request sent successfully!');
      setSelectedSong(null);
      setRequestForm({
        requester_name: '',
        requester_email: '',
        dedication: '',
        tip_amount: 0
      });
      
      setTimeout(() => setSuccess(''), 3000);
    } catch (error) {
      console.error('Error submitting request:', error);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Loading...</div>;
  }

  if (!musician) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Musician not found</div>;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-purple-400 mb-2">{musician.name}</h1>
            <p className="text-gray-300">Request your favorite songs!</p>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {success && (
          <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-4 mb-6 text-green-200">
            {success}
          </div>
        )}

        {/* Filters */}
        <div className="bg-gray-800 rounded-xl p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Filter Songs</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <select
              value={selectedFilters.genre}
              onChange={(e) => setSelectedFilters({...selectedFilters, genre: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
            >
              <option value="">All Genres</option>
              {filters.genres?.map((genre) => (
                <option key={genre} value={genre}>{genre}</option>
              ))}
            </select>
            
            <input
              type="text"
              placeholder="Artist name..."
              value={selectedFilters.artist}
              onChange={(e) => setSelectedFilters({...selectedFilters, artist: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
            />
            
            <select
              value={selectedFilters.mood}
              onChange={(e) => setSelectedFilters({...selectedFilters, mood: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
            >
              <option value="">All Moods</option>
              {filters.moods?.map((mood) => (
                <option key={mood} value={mood}>{mood}</option>
              ))}
            </select>
            
            <select
              value={selectedFilters.year}
              onChange={(e) => setSelectedFilters({...selectedFilters, year: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
            >
              <option value="">All Years</option>
              {filters.years?.map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Songs Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSongs.map((song) => (
            <div key={song.id} className="bg-gray-800 rounded-xl p-6 hover:bg-gray-700 transition duration-300">
              <h3 className="font-bold text-xl mb-2">{song.title}</h3>
              <p className="text-gray-300 mb-3">by {song.artist}</p>
              
              <div className="flex flex-wrap gap-2 mb-4">
                {song.genres.map((genre, idx) => (
                  <span key={idx} className="bg-blue-600 text-xs px-2 py-1 rounded">{genre}</span>
                ))}
                {song.moods.map((mood, idx) => (
                  <span key={idx} className="bg-green-600 text-xs px-2 py-1 rounded">{mood}</span>
                ))}
                {song.year && <span className="bg-gray-600 text-xs px-2 py-1 rounded">{song.year}</span>}
              </div>
              
              <button
                onClick={() => setSelectedSong(song)}
                className="w-full bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300"
              >
                Request This Song
              </button>
            </div>
          ))}
        </div>

        {filteredSongs.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-400 text-xl">No songs match your filters</p>
          </div>
        )}

        {/* Request Modal */}
        {selectedSong && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4">Request: {selectedSong.title}</h2>
              <p className="text-gray-300 mb-6">by {selectedSong.artist}</p>
              
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Your Name"
                  value={requestForm.requester_name}
                  onChange={(e) => setRequestForm({...requestForm, requester_name: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  required
                />
                
                <input
                  type="email"
                  placeholder="Your Email"
                  value={requestForm.requester_email}
                  onChange={(e) => setRequestForm({...requestForm, requester_email: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  required
                />
                
                <textarea
                  placeholder="Dedication message (optional)"
                  value={requestForm.dedication}
                  onChange={(e) => setRequestForm({...requestForm, dedication: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  rows="3"
                />
                
                <input
                  type="number"
                  placeholder="Tip Amount ($)"
                  value={requestForm.tip_amount}
                  onChange={(e) => setRequestForm({...requestForm, tip_amount: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  min="0"
                  step="0.01"
                />
              </div>
              
              <div className="flex space-x-4 mt-6">
                <button
                  onClick={() => setSelectedSong(null)}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg transition duration-300"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleRequest(selectedSong)}
                  className="flex-1 bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300"
                >
                  Send Request
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const LandingPage = () => {
  const [authMode, setAuthMode] = useState('login');

  return <AuthForm mode={authMode} onSwitch={setAuthMode} />;
};

const App = () => {
  const { musician } = useAuth();

  return (
    <Router>
      <Routes>
        <Route path="/" element={musician ? <Navigate to="/dashboard" /> : <LandingPage />} />
        <Route path="/dashboard" element={musician ? <MusicianDashboard /> : <Navigate to="/" />} />
        <Route path="/musician/:slug" element={<AudienceInterface />} />
      </Routes>
    </Router>
  );
};

const AppWithAuth = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWithAuth;