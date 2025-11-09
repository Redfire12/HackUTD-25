import { Paper, Typography, Box, Chip } from '@mui/material';
import { Warning } from '@mui/icons-material';

const StoryCard = ({ story }) => {
  const isFallback = story.source === 'fallback' || 
                     story.story?.includes('[Fallback]') || 
                     story.story?.includes('As a user, I want to address') ||
                     story.reason;

  return (
    <Paper elevation={2} sx={{ p: 3, transition: 'transform 0.2s', '&:hover': { transform: 'scale(1.02)' } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" fontWeight="bold">
          User Story
        </Typography>
        {isFallback && (
          <Chip
            icon={<Warning />}
            label="Using Fallback Data"
            color="warning"
            size="small"
          />
        )}
      </Box>
      <Typography
        variant="body1"
        sx={{
          whiteSpace: 'pre-wrap',
          color: 'text.primary',
          lineHeight: 1.6,
        }}
      >
        {story.story}
      </Typography>
    </Paper>
  );
};

export default StoryCard;
