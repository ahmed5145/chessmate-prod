import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import UserProfile from "../UserProfile";
import { getUserProfile, updateUserProfile } from "../../services/apiRequests";

jest.mock("react-hot-toast");
jest.mock("../../services/apiRequests");

const mockProfile = {
  username: "coachuser",
  email: "coach@example.com",
  rating: 1500,
  preferences: {
    emailNotifications: true,
    coach_persona: "encouraging",
    wants_reactivation_email: false,
  },
};

describe("CoachPersonaSettings", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getUserProfile.mockResolvedValue(mockProfile);
  });

  it("renders coach tone select and saves direct persona", async () => {
    updateUserProfile.mockResolvedValue({
      ...mockProfile,
      preferences: { ...mockProfile.preferences, coach_persona: "direct" },
    });

    render(
      <BrowserRouter>
        <UserProfile />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/coach tone/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/coach tone/i), {
      target: { value: "direct" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateUserProfile).toHaveBeenCalledWith({
        preferences: expect.objectContaining({ coach_persona: "direct" }),
      });
    });
  });
});
