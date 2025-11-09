import { Paper, Typography, Box, LinearProgress, Chip } from '@mui/material';
import { SentimentSatisfied, SentimentDissatisfied, SentimentNeutral } from '@mui/icons-material';

const SentimentCard = ({ sentiment }) => {
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

  const getSentimentIcon = (label) => {
    switch (label) {
      case 'positive':
        return <SentimentSatisfied sx={{ fontSize: 40, color: 'success.main' }} />;
      case 'negative':
        return <SentimentDissatisfied sx={{ fontSize: 40, color: 'error.main' }} />;
      default:
        return <SentimentNeutral sx={{ fontSize: 40, color: 'text.secondary' }} />;
    }
  };

  const sentimentValue = (sentiment.sentiment * 100).toFixed(1);
  const absoluteValue = Math.abs(sentiment.sentiment);

  return (
    <Paper elevation={2} sx={{ p: 3, transition: 'transform 0.2s', '&:hover': { transform: 'scale(1.02)' } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" fontWeight="bold">
          Sentiment Analysis
        </Typography>
        {getSentimentIcon(sentiment.label)}
      </Box>
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Score
          </Typography>
          <Typography variant="h6" fontWeight="bold" color={`${getSentimentColor(sentiment.label)}.main`}>
            {sentimentValue}%
          </Typography>
        </Box>
        <Box sx={{ position: 'relative', width: '100%', height: 8, bgcolor: 'grey.200', borderRadius: 1 }}>
          <LinearProgress
            variant="determinate"
            value={absoluteValue * 100}
            color={getSentimentColor(sentiment.label)}
            sx={{ height: 8, borderRadius: 1 }}
          />
        </Box>
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <Chip
          label={sentiment.label.toUpperCase()}
          color={getSentimentColor(sentiment.label)}
          sx={{ fontWeight: 'bold' }}
        />
      </Box>
    </Paper>
  );
};

export default SentimentCard;
