import React, { useState } from "react";
import "./LoginForm.css";

const LoginForm = ({ onLogin, isLoading }) => {
  const [studentId, setStudentId] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");

    // 학번 유효성 검사
    if (!studentId.trim()) {
      setError("학번을 입력해주세요.");
      return;
    }

    if (!/^\d{8}$/.test(studentId.trim())) {
      setError("학번은 8자리 숫자여야 합니다.");
      return;
    }

    onLogin(studentId.trim());
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>학생 인증</h2>
        <p>학번을 입력하여 인증해주세요</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label htmlFor="studentId">학번</label>
            <input
              type="text"
              id="studentId"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="예: 20230578"
              maxLength="8"
              disabled={isLoading}
              className={error ? "error" : ""}
            />
            {error && <span className="error-message">{error}</span>}
          </div>

          <button type="submit" disabled={isLoading} className="login-btn">
            {isLoading ? "인증 중..." : "인증하기"}
          </button>
        </form>

        <div className="login-info">
          <p>💡 등록된 학생만 이용 가능합니다</p>
          <p>🔒 개인정보는 안전하게 보호됩니다</p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;
