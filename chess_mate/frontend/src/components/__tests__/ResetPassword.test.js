import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { toast } from "react-toastify";
import ResetPassword from "../ResetPassword";
import { resetPassword } from "../../services/apiRequests";

// Mock the modules
jest.mock("react-toastify", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));
jest.mock("../../services/apiRequests");

jest.mock("../../context/ThemeContext", () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [new URLSearchParams("token=test-token")],
}));

const mockNavigate = jest.fn();

describe("ResetPassword Component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderWithRouter = () =>
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ResetPassword />
      </MemoryRouter>
    );

  it("renders the reset password form", () => {
    renderWithRouter();

    expect(screen.getByText("Reset Your Password")).toBeInTheDocument();
    expect(screen.getByLabelText("New Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm New Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset Password" })).toBeInTheDocument();
  });

  it("handles successful password reset", async () => {
    resetPassword.mockResolvedValueOnce({});

    renderWithRouter();

    const passwordInput = screen.getByLabelText("New Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm New Password");
    const submitButton = screen.getByRole("button", { name: "Reset Password" });

    fireEvent.change(passwordInput, { target: { value: "Newpassword123!" } });
    fireEvent.change(confirmPasswordInput, { target: { value: "Newpassword123!" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(resetPassword).toHaveBeenCalledWith("test-token", "Newpassword123!");
      expect(toast.success).toHaveBeenCalledWith("Password reset successful!");
    });

    // Wait for navigation
    await waitFor(
      () => {
        expect(mockNavigate).toHaveBeenCalledWith("/reset-password-success");
      },
      { timeout: 4000 }
    );
  });

  it("handles password reset error", async () => {
    const mockError = { response: { data: { message: "Invalid token" } } };
    resetPassword.mockRejectedValueOnce(mockError);

    renderWithRouter();

    const passwordInput = screen.getByLabelText("New Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm New Password");
    const submitButton = screen.getByRole("button", { name: "Reset Password" });

    fireEvent.change(passwordInput, { target: { value: "Newpassword123!" } });
    fireEvent.change(confirmPasswordInput, { target: { value: "Newpassword123!" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(resetPassword).toHaveBeenCalledWith("test-token", "Newpassword123!");
      expect(toast.error).toHaveBeenCalledWith("Invalid token");
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("shows error when passwords do not match", async () => {
    renderWithRouter();

    const passwordInput = screen.getByLabelText("New Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm New Password");
    const submitButton = screen.getByRole("button", { name: "Reset Password" });

    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.change(confirmPasswordInput, { target: { value: "password456" } });
    fireEvent.click(submitButton);

    expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it("shows loading state during submission", async () => {
    resetPassword.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    renderWithRouter();

    const passwordInput = screen.getByLabelText("New Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm New Password");
    const submitButton = screen.getByRole("button", { name: "Reset Password" });

    fireEvent.change(passwordInput, { target: { value: "Newpassword123!" } });
    fireEvent.change(confirmPasswordInput, { target: { value: "Newpassword123!" } });
    fireEvent.click(submitButton);

    expect(screen.getByText("Resetting Password...")).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  });
});
