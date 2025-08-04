import React, { useState } from "react";
import LoginForm from "./components/LoginForm";
import ChatInterface from "./components/ChatInterface";
import config from "./config";
import "./App.css";

function App() {
  const [authenticatedStudent, setAuthenticatedStudent] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (studentId) => {
    setIsLoading(true);
    try {
      // 학생 인증 API 호출
      const response = await fetch(`${config.API_URL}/api/auth/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ student_id: studentId }),
      });

      if (response.ok) {
        const studentData = await response.json();
        setAuthenticatedStudent(studentData);
      } else {
        const error = await response.json();
        alert(error.message || "인증에 실패했습니다.");
      }
    } catch (error) {
      console.error("Login error:", error);
      alert("서버 연결에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    setAuthenticatedStudent(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎓 학사 상담 AI 에이전트</h1>
        {authenticatedStudent && (
          <div className="user-info">
            <span>
              안녕하세요, {authenticatedStudent.name}님 (
              {authenticatedStudent.student_id})
            </span>
            <button onClick={handleLogout} className="logout-btn">
              로그아웃
            </button>
          </div>
        )}
      </header>

      <main className="App-main">
        {!authenticatedStudent ? (
          <LoginForm onLogin={handleLogin} isLoading={isLoading} />
        ) : (
          <ChatInterface studentData={authenticatedStudent} />
        )}
      </main>
    </div>
  );
}

export default App;
