import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { toast } from "react-hot-toast";
import ForgotPassword from "../ForgotPassword";
import { requestPasswordReset } from "../../services/apiRequests";

// Mock the modules
jest.mock("react-hot-toast");
jest.mock("../../services/apiRequests");

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

describe("ForgotPassword Component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the forgot password form", () => {
    render(
      <BrowserRouter>
        <ForgotPassword />
      </BrowserRouter>
    );

    expect(screen.getByText("Forgot Your Password?")).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send Reset Instructions" })).toBeInTheDocument();
  });

  it("handles successful password reset request", async () => {
    requestPasswordReset.mockResolvedValueOnce({});

    render(
      <BrowserRouter>
        <ForgotPassword />
      </BrowserRouter>
    );

    const emailInput = screen.getByLabelText("Email address");
    const submitButton = screen.getByRole("button", { name: "Send Reset Instructions" });

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(requestPasswordReset).toHaveBeenCalledWith("test@example.com");
      expect(toast.success).toHaveBeenCalledWith("Password reset instructions sent to your email");
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("handles password reset request error", async () => {
    const mockError = new Error("Invalid email");
    requestPasswordReset.mockRejectedValueOnce(mockError);

    render(
      <BrowserRouter>
        <ForgotPassword />
      </BrowserRouter>
    );

    const emailInput = screen.getByLabelText("Email address");
    const submitButton = screen.getByRole("button", { name: "Send Reset Instructions" });

    fireEvent.change(emailInput, { target: { value: "invalid@example.com" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(requestPasswordReset).toHaveBeenCalledWith("invalid@example.com");
      expect(toast.error).toHaveBeenCalledWith("Invalid email");
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("shows loading state during submission", async () => {
    requestPasswordReset.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(
      <BrowserRouter>
        <ForgotPassword />
      </BrowserRouter>
    );

    const emailInput = screen.getByLabelText("Email address");
    const submitButton = screen.getByRole("button", { name: "Send Reset Instructions" });

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.click(submitButton);

    expect(screen.getByText("Sending...")).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  });
});
