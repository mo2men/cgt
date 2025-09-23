import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#4a00e0', // Mystical purple
      light: '#8b5cf6',
      dark: '#1e1b4b',
    },
    secondary: {
      main: '#00d4ff', // Enchanted cyan
      light: '#06b6d4',
      dark: '#0e7490',
    },
    background: {
      default: '#f8fafc', // Soft ethereal background
      paper: '#ffffff',
    },
    text: {
      primary: '#1e293b',
      secondary: '#64748b',
    },
  },
  shadows: [
    'none',
    '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)',
    '0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23)',
    '0 10px 20px rgba(74,0,224,0.19), 0 6px 6px rgba(0,212,255,0.23)',
    '0 14px 28px rgba(74,0,224,0.25), 0 10px 10px rgba(0,212,255,0.22)',
    '0 19px 38px rgba(74,0,224,0.30), 0 15px 12px rgba(0,212,255,0.22)',
    '0 24px 48px rgba(74,0,224,0.35), 0 20px 20px rgba(0,212,255,0.23)',
    '0 30px 60px rgba(74,0,224,0.40), 0 25px 25px rgba(0,212,255,0.24)',
    '0 36px 72px rgba(74,0,224,0.45), 0 30px 30px rgba(0,212,255,0.25)',
    '0 42px 84px rgba(74,0,224,0.50), 0 35px 35px rgba(0,212,255,0.26)',
    '0 48px 96px rgba(74,0,224,0.55), 0 40px 40px rgba(0,212,255,0.27)',
    '0 54px 108px rgba(74,0,224,0.60), 0 45px 45px rgba(0,212,255,0.28)',
    '0 60px 120px rgba(74,0,224,0.65), 0 50px 50px rgba(0,212,255,0.29)',
    '0 66px 132px rgba(74,0,224,0.70), 0 55px 55px rgba(0,212,255,0.30)',
    '0 72px 144px rgba(74,0,224,0.75), 0 60px 60px rgba(0,212,255,0.31)',
    '0 78px 156px rgba(74,0,224,0.80), 0 65px 65px rgba(0,212,255,0.32)',
    '0 84px 168px rgba(74,0,224,0.85), 0 70px 70px rgba(0,212,255,0.33)',
    '0 90px 180px rgba(74,0,224,0.90), 0 75px 75px rgba(0,212,255,0.34)',
    '0 96px 192px rgba(74,0,224,0.95), 0 80px 80px rgba(0,212,255,0.35)',
    '0 102px 204px rgba(74,0,224,1.00), 0 85px 85px rgba(0,212,255,0.36)',
    '0 108px 216px rgba(74,0,224,1.00), 0 90px 90px rgba(0,212,255,0.37)',
    '0 114px 228px rgba(74,0,224,1.00), 0 95px 95px rgba(0,212,255,0.38)',
    '0 120px 240px rgba(74,0,224,1.00), 0 100px 100px rgba(0,212,255,0.39)',
    '0 126px 252px rgba(74,0,224,1.00), 0 105px 105px rgba(0,212,255,0.40)',
    '0 132px 264px rgba(74,0,224,1.00), 0 110px 110px rgba(0,212,255,0.41)',
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          borderRadius: '8px',
          boxShadow: '0 4px 14px 0 rgba(74, 0, 224, 0.2)',
          '&:hover': {
            boxShadow: '0 8px 25px 0 rgba(74, 0, 224, 0.3), 0 0 20px rgba(0, 212, 255, 0.5)',
            transform: 'translateY(-2px)',
          },
          '&:active': {
            transform: 'translateY(0)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(255, 255, 255, 0.2)',
          background: 'linear-gradient(145deg, #ffffff, #f0f4ff)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '16px',
          boxShadow: '0 12px 40px rgba(74, 0, 224, 0.1)',
          transition: 'all 0.3s ease',
          '&:hover': {
            boxShadow: '0 20px 60px rgba(74, 0, 224, 0.15), 0 0 30px rgba(0, 212, 255, 0.2)',
            transform: 'translateY(-4px)',
          },
        },
      },
    },
  },
});

export default theme;