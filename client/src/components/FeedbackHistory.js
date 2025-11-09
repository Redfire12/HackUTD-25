import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  AppBar,
  Toolbar,
  Button,
  Stack,
  Grid,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { Delete as DeleteIcon } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { feedbackAPI } from '../services/api';
import SentimentCard from './SentimentCard';
import StoryCard from './StoryCard';
import InsightsCard from './InsightsCard';

const FeedbackHistory = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFeedback, setSelectedFeedback] = useState(null);
  const [error, setError] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [feedbackToDelete, setFeedbackToDelete] = useState(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await feedbackAPI.getHistory();
      setHistory(response.data);
    } catch (err) {
      console.error('Error loading history:', err);
      setError('Failed to load feedback history');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (id) => {
    setFeedbackToDelete(id);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!feedbackToDelete) return;

    try {
      await feedbackAPI.deleteFeedback(feedbackToDelete);
      setHistory(history.filter((item) => item.id !== feedbackToDelete));
      if (selectedFeedback?.id === feedbackToDelete) {
        setSelectedFeedback(null);
      }
      setDeleteDialogOpen(false);
      setFeedbackToDelete(null);
    } catch (err) {
      console.error('Error deleting feedback:', err);
      setError('Failed to delete feedback');
    }
  };

  const getSentimentColor = (label) => {
    switch (label) {
      case 'positive':
        return 'success';
      case 'negative':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'white', color: 'text.primary' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            Feedback History
          </Typography>
          <Typography variant="body2" sx={{ mr: 2, color: 'text.secondary' }}>
            View your analyzed feedback
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button color="inherit" onClick={() => navigate('/dashboard')}>
              Dashboard
            </Button>
            <Button color="error" variant="contained" onClick={logout}>
              Logout
            </Button>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Paper elevation={2} sx={{ p: 2, maxHeight: '600px', overflow: 'auto' }}>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Your Feedback ({history.length})
              </Typography>
              {history.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No feedback submitted yet.
                </Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 2 }}>
                  {history.map((item) => (
                    <Paper
                      key={item.id}
                      variant="outlined"
                      sx={{
                        p: 2,
                        cursor: 'pointer',
                        bgcolor: selectedFeedback?.id === item.id ? 'primary.light' : 'background.paper',
                        '&:hover': {
                          bgcolor: 'action.hover',
                        },
                      }}
                      onClick={() => setSelectedFeedback(item)}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Chip
                          label={item.sentiment_label}
                          color={getSentimentColor(item.sentiment_label)}
                          size="small"
                        />
                        <IconButton
                          size="small"
                          color="error"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteClick(item.id);
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                      <Typography variant="body2" sx={{ mb: 1, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                        {item.text}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(item.created_at).toLocaleDateString()}
                      </Typography>
                    </Paper>
                  ))}
                </Box>
              )}
            </Paper>
          </Grid>

          <Grid item xs={12} md={8}>
            {selectedFeedback ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <Paper elevation={2} sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom fontWeight="bold">
                    Feedback Details
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    {selectedFeedback.text}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Submitted: {new Date(selectedFeedback.created_at).toLocaleString()}
                  </Typography>
                </Paper>

                <Grid container spacing={2}>
                  {selectedFeedback.sentiment && (
                    <Grid item xs={12} md={6}>
                      <SentimentCard
                        sentiment={{
                          sentiment: selectedFeedback.sentiment,
                          label: selectedFeedback.sentiment_label,
                        }}
                      />
                    </Grid>
                  )}
                  {selectedFeedback.user_story && (
                    <Grid item xs={12} md={6}>
                      {(() => {
                        const storyText = selectedFeedback.user_story || '';
                        const isFallback = storyText.includes('[Fallback]') ||
                          storyText.includes('As a user, I want to address') ||
                          storyText.length < 50;
                        return (
                      <StoryCard
                        story={{
                          story: selectedFeedback.user_story,
                              source: isFallback ? 'fallback' : (selectedFeedback.insights?.source || 'openai'),
                              reason: selectedFeedback.insights?.reason,
                        }}
                      />
                        );
                      })()}
                    </Grid>
                  )}
                </Grid>

                {selectedFeedback.insights && Object.keys(selectedFeedback.insights).length > 0 && (
                  <InsightsCard insights={selectedFeedback.insights} />
                )}
              </Box>
            ) : (
              <Paper elevation={2} sx={{ p: 6, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  Select a feedback item to view details
                </Typography>
              </Paper>
            )}
          </Grid>
        </Grid>
      </Container>

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Feedback?</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this feedback? This action cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default FeedbackHistory;
