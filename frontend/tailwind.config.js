module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#ff006e',      // Hot pink
        secondary: '#8338ec',    // Purple
        accent: '#06ffa5',       // Neon cyan
        dark: '#0a0a0f',         // Deep black
        darker: '#050508',       // Darker black
        danger: '#ff006e',
        success: '#06ffa5',
        warning: '#ffbe0b',
      },
      backgroundImage: {
        'gta-gradient': 'linear-gradient(135deg, #8338ec 0%, #ff006e 100%)',
        'gta-gradient-dark': 'linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 100%)',
      },
    }
  },
  plugins: []
}
