export function getPrimaryChunk(chatResponse) {
  const chunks = chatResponse?.chunks;
  if (!Array.isArray(chunks) || chunks.length === 0) return null;
  return chunks[0];
}

export function confidenceLabelFromCombined(combinedScore, threshold = 0.7) {
  if (combinedScore == null || Number.isNaN(combinedScore)) return 'N/A';
  const distance = Math.abs(combinedScore - threshold);
  if (distance >= 0.25) return 'High';
  if (distance >= 0.1) return 'Medium';
  return 'Low';
}
