import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Credits from "../Credits";
import { UserContext } from "../../contexts/UserContext";
import api from "../../services/api";

jest.mock("../../services/api");
jest.mock("../../context/ThemeContext", () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

const userContextValue = {
  credits: 20,
  fetchUserData: jest.fn(),
};

const mockReferral = {
  referral_link: "http://localhost:3000/register?ref=coach-abc",
  referrer_credits: 5,
  referee_bonus_credits: 5,
  successful_referrals: 2,
  monthly_cap: 10,
};

describe("ReferralCredits", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.get.mockImplementation((url) => {
      if (url === "/api/v1/profile/referral/") {
        return Promise.resolve({ data: mockReferral });
      }
      if (url === "/api/v1/credits/packages/") {
        return Promise.resolve({
          data: {
            signup_bonus_credits: 15,
            packages: [],
            summary_points: ["New accounts receive 15 free credits"],
          },
        });
      }
      return Promise.reject(new Error(`Unexpected GET ${url}`));
    });
    Object.assign(navigator, {
      clipboard: { writeText: jest.fn().mockResolvedValue(undefined) },
    });
  });

  it("renders invite card and copies referral link", async () => {
    render(
      <BrowserRouter>
        <UserContext.Provider value={userContextValue}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/invite a friend/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/2 successful referrals/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /copy referral link/i }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockReferral.referral_link);
    });
  });
});
