import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const PERSON_STATUS_COLORS: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  review: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  published: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  archived: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

export const PERSON_TYPE_COLORS: Record<string, string> = {
  saint: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  blessed: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400",
  venerable: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  servant_of_god: "bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400",
  candidate: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};
