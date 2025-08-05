// static/js/firebaseConfig.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { getAuth }        from "https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js";
import { getAnalytics }   from "https://www.gstatic.com/firebasejs/9.22.0/firebase-analytics.js";


// Your web app's Firebase configuration
// Replace these values with your Firebase project settings
const firebaseConfig = {
  apiKey: "AIzaSyBzgB6KsEmncRvh3bQTaPUp8Z2qWNCtRdM",
  authDomain: "hopekcc-8dc3b.firebaseapp.com",
  projectId: "hopekcc-8dc3b",
  storageBucket: "hopekcc-8dc3b.appspot.com",
  messagingSenderId: "225646371816",
  appId: "1:225646371816:web:db29567f34f0f071203a5d",
  measurementId: "G-Q1QJSQS2NY"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
// Initialize Firebase Authentication and get a reference to the service
const auth = getAuth(app);
// Initialize Analytics (optional)
const analytics = getAnalytics(app);

export { app, auth, analytics };