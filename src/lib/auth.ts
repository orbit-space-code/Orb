import { NextAuthOptions } from "next-auth"
import GithubProvider from "next-auth/providers/github"
import { PrismaAdapter } from "@next-auth/prisma-adapter"
import { PrismaClient } from "@prisma/client"

const prisma = new PrismaClient()

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "read:user user:email repo",
        },
      },
    }),
  ],
  callbacks: {
    async session({ session, token, user }) {
      if (session.user) {
        session.user.id = user.id
      }
      return session
    },
    async signIn({ user, account, profile }) {
      if (account?.provider === "github" && profile) {
        // Store GitHub access token for repository operations
        await prisma.user.upsert({
          where: { githubId: (profile as any).id },
          update: {
            accessToken: account.access_token!,
            username: (profile as any).login,
            email: (profile as any).email,
            avatarUrl: (profile as any).avatar_url,
          },
          create: {
            githubId: (profile as any).id,
            username: (profile as any).login,
            email: (profile as any).email,
            avatarUrl: (profile as any).avatar_url,
            accessToken: account.access_token!,
          },
        })
      }
      return true
    },
  },
  pages: {
    signIn: "/",
  },
  session: {
    strategy: "jwt",
  },
}
