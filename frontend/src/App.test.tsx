import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';

const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockResolvedValue({
    ok: true,
    json: async () => ({
      page: 1,
      page_size: 20,
      total: 0,
      total_pages: 0,
      items: [],
    }),
  });
  global.fetch = fetchMock;
});

afterEach(() => {
  fetchMock.mockReset();
});

test('renders recall search controls', async () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: /food recall search/i })).toBeInTheDocument();
  expect(screen.getByRole('searchbox')).toBeInTheDocument();
  expect(screen.getByLabelText(/classification/i)).toBeInTheDocument();
  expect(screen.queryByLabelText(/source/i)).not.toBeInTheDocument();
  expect(screen.getByLabelText(/ongoing recalls only/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/sort/i)).toBeInTheDocument();

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith('/api/recalls?page=1&page_size=20&sort=relevance', {
      signal: expect.any(AbortSignal),
    });
  });
  expect(await screen.findByText(/0 results/i)).toBeInTheDocument();
});

test('filters recalls by selected classification', async () => {
  render(<App />);
  await screen.findByText(/0 results/i);

  fireEvent.change(screen.getByLabelText(/classification/i), {
    target: { value: 'Class II' },
  });
  fireEvent.click(screen.getByRole('button', { name: /search/i }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/recalls?page=1&page_size=20&sort=relevance&classification=Class+II',
      {
        signal: expect.any(AbortSignal),
      }
    );
  });
});

test('filters to ongoing recalls when checkbox is checked', async () => {
  render(<App />);
  await screen.findByText(/0 results/i);

  fireEvent.click(screen.getByLabelText(/ongoing recalls only/i));
  fireEvent.click(screen.getByRole('button', { name: /search/i }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenLastCalledWith('/api/recalls?page=1&page_size=20&sort=relevance&status=Ongoing', {
      signal: expect.any(AbortSignal),
    });
  });
});
