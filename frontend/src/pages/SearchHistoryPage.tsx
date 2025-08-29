import React, { useState, useEffect } from 'react';
import { searchAPI, Article } from '../services/api';
import {
  Container,
  Typography,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Button,
  Box,
  Paper,
  CircularProgress,
  Snackbar,
  Alert,
} from '@mui/material';
import { Delete as DeleteIcon } from '@mui/icons-material';

const SearchHistoryPage: React.FC = () => {
  const [history, setHistory] = useState<Article[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const data = await searchAPI.getSearchHistoryFile();
        setHistory(data);
        setError(null);
      } catch (err) {
        setError('Failed to load search history.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const handleDelete = (articleTitle: string) => {
    setHistory(prevHistory => prevHistory.filter(article => article.title !== articleTitle));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await searchAPI.updateSearchHistoryFile(history);
      setSuccess('Search history updated successfully!');
      setError(null);
    } catch (err) {
      setError('Failed to save search history.');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleCloseSnackbar = () => {
    setError(null);
    setSuccess(null);
  };

  if (loading) {
    return (
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Manage Search History
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Here you can view and delete entries from the `search_history.json` file. This affects the "Exclude Duplicates" feature in searches.
        </Typography>
        
        <List>
          {history.length > 0 ? (
            history.map((article, index) => (
              <ListItem
                key={`${article.title}-${index}`}
                divider
                secondaryAction={
                  <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(article.title)}>
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <ListItemText
                  primary={article.title}
                  secondary={`Authors: ${article.authors || 'N/A'} - Year: ${article.year || 'N/A'}`}
                />
              </ListItem>
            ))
          ) : (
            <Typography sx={{ textAlign: 'center', p: 2 }}>
              Search history is empty.
            </Typography>
          )}
        </List>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSave}
            disabled={saving}
            startIcon={saving ? <CircularProgress size={20} /> : null}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </Paper>

      <Snackbar open={!!error} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
      <Snackbar open={!!success} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity="success" sx={{ width: '100%' }}>
          {success}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default SearchHistoryPage;