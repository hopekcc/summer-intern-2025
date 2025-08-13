// static/js/firebaseConfig.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { getAuth }        from "https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js";
import { getAnalytics }   from "https://www.gstatic.com/firebasejs/9.22.0/firebase-analytics.js";


// Your web app's Firebase configuration
// Replace these values with your Firebase project settings
const firebaseConfig = {
  apiKey: "AIzaSyAQ3r-8kqsWOgBkWRKs-bApV33oeu-AICs",
  authDomain: "hopekcc-2024-summer-intern-api.firebaseapp.com",
  projectId: "hopekcc-2024-summer-intern-api",
  storageBucket: "hopekcc-2024-summer-intern-api.firebasestorage.app",
  messagingSenderId: "172531116306",
  appId: "1:172531116306:web:d898ae28b5f79a425babcb"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
// Initialize Firebase Authentication and get a reference to the service
const auth = getAuth(app);
// Initialize Analytics (optional)
const analytics = getAnalytics(app);

export { app, auth, analytics };