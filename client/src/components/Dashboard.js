import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  AppBar,
  Toolbar,
  Stack,
  Snackbar,
} from '@mui/material';
import { Warning as WarningIcon, CheckCircle as CheckCircleIcon } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { feedbackAPI } from '../services/api';
import SentimentCard from './SentimentCard';
import StoryCard from './StoryCard';
import InsightsCard from './InsightsCard';

const Dashboard = () => {
  const [feedback, setFeedback] = useState('');
  const [sentiment, setSentiment] = useState(null);
  const [story, setStory] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fallbackWarning, setFallbackWarning] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async () => {
    if (!feedback.trim()) {
      setError('Please enter some feedback');
      return;
    }

    setLoading(true);
    setError('');
    setFallbackWarning(false);
    setSentiment(null);
    setStory(null);
    setInsights(null);

    try {
      const response = await feedbackAPI.submit(feedback);
      const data = response.data;

      const sentimentData = {
        sentiment: data.sentiment,
        label: data.sentiment_label,
      };
      setSentiment(sentimentData);
      
      // Parse insights to check for fallback
      let insightsData = data.insights || {};
      if (typeof insightsData === 'string') {
        try {
          insightsData = JSON.parse(insightsData);
        } catch (e) {
          insightsData = {};
        }
      }
      
      // Check if story is using fallback
      const storyText = data.user_story || '';
      const isStoryFallback = storyText.includes('[Fallback]') || 
                              storyText.includes('As a user, I want to address') ||
                              !storyText || storyText.length < 50;
      
      const storyData = {
        story: storyText,
        source: isStoryFallback ? 'fallback' : 'openai',
        reason: isStoryFallback ? 'API unavailable' : undefined,
      };
      setStory(storyData);
      
      // Check if insights are using fallback
      const isInsightsFallback = insightsData.source === 'fallback' || 
                                 insightsData.reason ||
                                 (!insightsData.source && insightsData.summary?.includes('unavailable')) ||
                                 (!insightsData.source && insightsData.themes?.length === 1 && insightsData.themes[0]?.name === 'General Feedback');
      
      if (isInsightsFallback || isStoryFallback) {
        setFallbackWarning(true);
      }
      
      setInsights(insightsData);

      setFeedback('');
      setSuccessOpen(true);
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError(err.response?.data?.detail || 'Failed to analyze feedback');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'white', color: 'text.primary' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            Feedback Dashboard
          </Typography>
          <Typography variant="body2" sx={{ mr: 2, color: 'text.secondary' }}>
            Welcome back, {user?.username}!
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button color="inherit" onClick={() => navigate('/history')}>
              View History
            </Button>
            <Button color="error" variant="contained" onClick={logout}>
              Logout
            </Button>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        {/* Fallback Warning Banner */}
        {fallbackWarning && (
          <Alert 
            severity="warning" 
            icon={<WarningIcon />}
            sx={{ mb: 3 }}
            onClose={() => setFallbackWarning(false)}
          >
            ⚠️ Using fallback data — API quota or key issue. Please check your OpenAI API key configuration.
          </Alert>
        )}

        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom fontWeight="bold">
            Analyze Customer Feedback
          </Typography>
          <Box sx={{ mt: 3 }}>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Enter customer feedback"
              variant="outlined"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              disabled={loading}
              sx={{ mb: 2 }}
              placeholder="Example: The checkout process is too slow and confusing. I abandoned my cart three times before completing a purchase."
            />
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            <Button
              variant="contained"
              size="large"
              fullWidth
              onClick={handleSubmit}
              disabled={loading || !feedback.trim()}
              sx={{
                background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #0369a1 0%, #075985 100%)',
                },
              }}
            >
              {loading ? (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={20} color="inherit" />
                  <span>Analyzing...</span>
                </Box>
              ) : (
                'Analyze Feedback'
              )}
            </Button>
          </Box>
        </Paper>

        {loading && (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4, gap: 2 }}>
            <CircularProgress />
            <Typography variant="body2" color="text.secondary">
              Analyzing feedback and generating insights...
            </Typography>
          </Box>
        )}

        {!loading && (sentiment || story || insights) && (
          <>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 3, mb: 3 }}>
              {sentiment && <SentimentCard sentiment={sentiment} />}
              {story && <StoryCard story={story} />}
            </Box>

            {insights && Object.keys(insights).length > 0 && (
              <InsightsCard insights={insights} />
            )}
          </>
        )}
      </Container>

      <Snackbar
        open={successOpen}
        autoHideDuration={4000}
        onClose={() => setSuccessOpen(false)}
        message={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircleIcon fontSize="small" />
            <Typography variant="body2">Analysis complete</Typography>
          </Box>
        }
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default Dashboard;
