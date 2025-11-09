import { Paper, Typography, Box, Chip, Alert } from '@mui/material';
import { Warning } from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const InsightsCard = ({ insights }) => {
  const isFallback = insights?.source === 'fallback' || 
                     insights?.reason ||
                     (!insights?.source && insights?.summary?.includes('unavailable'));

  const themesData = insights?.themes?.map((theme) => ({
    name: theme.name || 'Unknown',
    sentiment: ((theme.sentiment || 0) * 100).toFixed(1),
    count: theme.count || 1,
  })) || [];

  const sentimentDistribution = [
    {
      name: 'Positive',
      value: themesData.filter((t) => parseFloat(t.sentiment) > 10).length,
    },
    {
      name: 'Neutral',
      value: themesData.filter((t) => parseFloat(t.sentiment) >= -10 && parseFloat(t.sentiment) <= 10).length,
    },
    {
      name: 'Negative',
      value: themesData.filter((t) => parseFloat(t.sentiment) < -10).length,
    },
  ].filter((item) => item.value > 0);

  const COLORS = ['#10b981', '#6b7280', '#ef4444'];

  return (
    <Paper elevation={2} sx={{ p: 3, transition: 'transform 0.2s', '&:hover': { transform: 'scale(1.01)' } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight="bold">
          Insights & Analytics
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

      {insights?.summary && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
            Summary
          </Typography>
          <Typography variant="body2">{insights.summary}</Typography>
        </Alert>
      )}

      {themesData && themesData.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Themes Sentiment
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={themesData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="sentiment" fill="#0284c7" name="Sentiment Score (%)" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      )}

      {sentimentDistribution.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Sentiment Distribution
          </Typography>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={sentimentDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {sentimentDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Box>
      )}

      {themesData && themesData.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Key Themes
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {themesData.map((theme, index) => (
              <Paper
                key={index}
                variant="outlined"
                sx={{
                  p: 2,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Typography variant="body1" fontWeight="medium">
                  {theme.name}
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    Count: {theme.count}
                  </Typography>
                  <Chip
                    label={`${theme.sentiment}%`}
                    color={
                      parseFloat(theme.sentiment) > 0
                        ? 'success'
                        : parseFloat(theme.sentiment) < 0
                        ? 'error'
                        : 'default'
                    }
                    size="small"
                  />
                </Box>
              </Paper>
            ))}
          </Box>
        </Box>
      )}

      {insights?.anomalies && insights.anomalies.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Anomalies & Alerts
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {insights.anomalies.map((anomaly, index) => (
              <Alert key={index} severity="warning">
                {anomaly}
              </Alert>
            ))}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default InsightsCard;
